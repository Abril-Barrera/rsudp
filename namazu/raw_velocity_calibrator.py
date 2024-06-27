import socket
import obspy
import numpy as np
import logging
import ast
import time
import matplotlib.pyplot as plt
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

pre_filt = [0.01, 0.02, 20.0, 50.0]

def initialize_socket(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    logging.info(f"Listening for data on {ip}:{port}")
    return sock

def process_data(sock, inventory, duration):
    start_time = time.time()
    counter = 0
    local_raw_data = []
    local_velocity_data = []
    adjusted_start_time = None

    first_record_logged = False

    while time.time() - start_time < duration:
        data, addr = sock.recvfrom(4096)
        adjusted_start_time, local_raw_data, local_velocity_data = process_single_data(data, counter, inventory, adjusted_start_time, local_raw_data, local_velocity_data, first_record_logged)
        if counter == 0:
            first_record_logged = True
        counter += 1

    return local_raw_data, local_velocity_data, adjusted_start_time

def process_single_data(data, counter, inventory, adjusted_start_time, local_raw_data, local_velocity_data, first_record_logged):
    try:
        data_str = data.decode('utf-8')
        data_str = data_str.replace('{', '[').replace('}', ']')
        parsed_data = ast.literal_eval(data_str)

        sensor_timestamp = parsed_data[1]

        seismic_readings = parsed_data[2:]
        np_data = np.array(seismic_readings, dtype=np.int32)
        local_raw_data.extend(np_data.tolist())

        if not first_record_logged:
            logging.info(f"Raw seismic readings w time (first 10): {parsed_data}")
            logging.info(f"Raw seismic readings (first 10): {np_data[:10]}")

        trace = obspy.Trace(data=np_data)
        trace.stats.network = 'AM'
        trace.stats.station = 'RECF8'
        trace.stats.location = '00'
        trace.stats.channel = 'EHZ'
        trace.stats.starttime = obspy.UTCDateTime(sensor_timestamp)
        trace.stats.sampling_rate = 100.0
        st = obspy.Stream(traces=[trace])
        st.attach_response(inventory)
        st.remove_response(inventory=inventory, output="VEL", pre_filt=pre_filt, taper=True, water_level=60)

        
        if counter == 0:
            logging.info(f"Sensor timestamp: {counter} - {sensor_timestamp}")
            logging.info(f"Local Trace Attributes: {st[0].stats}")
            adjusted_start_time = obspy.UTCDateTime(sensor_timestamp)

        local_velocity_data.extend(st[0].data.tolist())

    except Exception as e:
        logging.error(f"Error processing data: {e}")
        
    return adjusted_start_time, local_raw_data, local_velocity_data

def get_local_data(sock, duration):
    inventory_path = "namazu/inventory.xml"
    inventory = obspy.read_inventory(inventory_path)
    return process_data(sock, inventory, duration)

def get_server_data(station, duration, adjusted_start_time, inventory, client):
    end_time = adjusted_start_time + duration
    st = client.get_waveforms(network="AM", station=station, location="00", channel="EHZ", starttime=adjusted_start_time, endtime=end_time)
    st.attach_response(inventory)
    server_raw_data = st[0].data

    logging.info(f"Server raw data (first 10): {server_raw_data[:10]}")

    st.remove_response(inventory=inventory, output="VEL", pre_filt=pre_filt, taper=True, water_level=60)
    server_velocity_data = st[0].data
    logging.info(f"Server velocity data (first 10): {server_velocity_data[:10]}")

    logging.info(f"Server Trace Attributes: {st[0].stats}")

    times = np.arange(0, duration, st[0].stats.delta)

    return server_raw_data, server_velocity_data, times

def resample_data(data, original_rate, target_rate):
    if original_rate != target_rate:
        data = obspy.signal.filter.envelope(data)
        data = obspy.signal.invsim.resample(data, original_rate, target_rate)
    return data

def get_data_statistics(times, server_raw_data, local_raw_data, server_velocity_data, local_velocity_data):
    min_length = min(len(times), len(server_raw_data), len(local_raw_data), len(server_velocity_data), len(local_velocity_data))
    times = times[:min_length]
    server_raw_data = server_raw_data[:min_length]
    local_raw_data = np.array(local_raw_data[:min_length])
    server_velocity_data = server_velocity_data[:min_length]
    local_velocity_data = np.array(local_velocity_data[:min_length])

    return times, server_raw_data, local_raw_data, server_velocity_data, local_velocity_data

def plot_velocity_data(times, local_velocity_data, server_velocity_data):
    plt.figure(figsize=(12, 6))

    plt.subplot(2, 1, 1)
    plt.plot(times[:len(local_velocity_data)], local_velocity_data, label='Local Velocity', color='green', alpha=0.7)
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Local Velocity Data')
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(times[:len(server_velocity_data)], server_velocity_data, label='Server Velocity', color='blue', alpha=0.7)
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Server Velocity Data')
    plt.legend()

    plt.tight_layout()
    plt.show()

def plot_raw_data(times, server_raw_data, local_raw_data):
    plt.figure(figsize=(12, 6))
    plt.plot(times, server_raw_data, label='Server Raw Data', color='red', linestyle='-', linewidth=1.5, marker='o', markersize=2)
    plt.plot(times, local_raw_data, label='Local Raw Data', color='blue', linestyle='--', linewidth=1.5, marker='x', markersize=2)
    plt.xlabel('Time (s)')
    plt.ylabel('Raw Data')
    plt.title('Raw Data Comparison Between Server and Local')
    plt.legend()
    plt.show()

def calculate_similarity(data1, data2):
    if len(data1) == 0 or len(data2) == 0:
        return 0.0
    data1 = data1.reshape(1, -1)
    data2 = data2.reshape(1, -1)
    similarity = cosine_similarity(data1, data2)
    return similarity[0][0] * 100


def main():
    logging.info("----------------- Process started ----------------- ")
    logging.info("----------------- Current configuration ----------------- ")
    station = "RECF8"
    duration = 5
    start_time = UTCDateTime.now()
    inventory_path = "namazu/inventory.xml"
    ip = "192.168.1.73"
    port = 8888
    client = Client("https://data.raspberryshake.org")
    inventory = obspy.read_inventory(inventory_path)
    sock = initialize_socket(ip, port)
    logging.info(f"Station: {station}")
    logging.info(f"Duration: {station}")
    logging.info(f"Start Time: {start_time}")

    logging.info("----------------- Getting local raw & velocity data ----------------- ")
    local_raw_data, local_velocity_data, adjusted_start_time = get_local_data(sock, duration)

    logging.info("----------------- Getting server raw & velocity data ----------------- ")
    server_raw_data, server_velocity_data, times = get_server_data(station, duration, adjusted_start_time, inventory, client)

    logging.info("----------------- Calculating data statistics ----------------- ")
    times, server_raw_data, local_raw_data, server_velocity_data, local_velocity_data = get_data_statistics(times, server_raw_data, local_raw_data, server_velocity_data, local_velocity_data)

    similarity_raw = calculate_similarity(server_raw_data, local_raw_data)
    logging.info(f"Similarity between server raw data and local raw data: {similarity_raw:.2f}%")

    similarity_velocity = calculate_similarity(server_velocity_data, local_velocity_data)
    logging.info(f"Similarity between server velocity data and local velocity data: {similarity_velocity:.2f}%")

    logging.info("----------------- Generating plots for velocity and raw data ----------------- ")
    plot_raw_data(times, server_raw_data, local_raw_data)
    plot_velocity_data(times, local_velocity_data, server_velocity_data)

    logging.info("----------------- Process completed ----------------- ")

if __name__ == "__main__":
    main()