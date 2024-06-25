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

class RealTimeSeismograph:
    def __init__(self, ip, port, inventory_path):
        self.ip = ip
        self.port = port
        self.inventory = obspy.read_inventory(inventory_path)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        self.local_velocity_data = []
        self.local_raw_data = []
        self.adjusted_start_time = None
        logging.info(f"Listening for data on {self.ip}:{self.port}")

    def process_data(self, data, counter, duration):
        try:
            data_str = data.decode('utf-8')
            data_str = data_str.replace('{', '[').replace('}', ']')
            parsed_data = ast.literal_eval(data_str)

            sensor_timestamp = parsed_data[1]
            if counter == 0:
                logging.info(f"Sensor timestamp: {counter} + ' - ' + {sensor_timestamp}")
                self.adjusted_start_time = obspy.UTCDateTime(sensor_timestamp)

            seismic_readings = parsed_data[2:]
            np_data = np.array(seismic_readings, dtype=np.int32)

            self.local_raw_data.extend(np_data.tolist())

            trace = obspy.Trace(data=np_data)
            trace.stats.network = 'AM'
            trace.stats.station = 'RECF8'
            trace.stats.location = '00'
            trace.stats.channel = 'EHZ'
            trace.stats.starttime = obspy.UTCDateTime(sensor_timestamp)

            st = obspy.Stream(traces=[trace])
            st.attach_response(self.inventory)

            st.detrend("demean")
            st.taper(max_percentage=0.05, type='hann')

            nyquist = 0.5 * st[0].stats.sampling_rate
            freqmin = 0.1
            freqmax = min(5.0, nyquist - 0.1)  # Ensure freqmax is below Nyquist

            st.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, zerophase=True)
            
            pre_filt = [0.1, 0.2, freqmax, nyquist]
            st.remove_response(output="VEL", pre_filt=pre_filt)
            velocity_data = st[0].data

            if velocity_data.size > 0:
                self.local_velocity_data.extend(velocity_data.tolist())
            else:
                logging.warning("Processed local velocity data is empty.")

        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def run(self, period):
        start_time = time.time()
        counter = 0
        while time.time() - start_time < period:
            data, addr = self.sock.recvfrom(4096)
            self.process_data(data, counter, period)
            elapsed_time = int(time.time() - start_time)
            counter += 1

def adjust_baseline(trace):
    baseline = np.mean(trace.data)
    trace.data = trace.data - baseline
    logging.debug(f"Adjusted baseline: {baseline}")
    return trace

def calculate_similarity(data1, data2):
    if len(data1) == 0 or len(data2) == 0:
        return 0.0
    data1 = data1.reshape(1, -1)
    data2 = data2.reshape(1, -1)
    similarity = cosine_similarity(data1, data2)
    return similarity[0][0] * 100

def fetch_and_process_data(station, duration, local_velocity_data, local_raw_data, adjusted_start_time):
    client = None
    retries = 5
    for attempt in range(retries):
        try:
            client = Client("https://data.raspberryshake.org")
            break
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}/{retries} - Error connecting to FDSN service: {e}")
            time.sleep(5)
    if client is None:
        logging.error("Failed to connect to FDSN service after multiple attempts.")
        return
    
    end_time = adjusted_start_time + duration
    try:
        st = client.get_waveforms(network="AM", station=station, location="00", channel="EHZ", starttime=adjusted_start_time, endtime=end_time)
    except Exception as e:
        logging.error(f"No data available for request: {e}")
        return
    
    try:
        inventory = client.get_stations(network="AM", station=station, level="response")
    except Exception as e:
        logging.error(f"Error fetching inventory: {e}")
        return
    
    st = st.copy()
    for trace in st:
        trace = adjust_baseline(trace)
    
    st.remove_response(inventory=inventory, output="VEL")
    server_velocities = st[0].data

    times = np.arange(0, duration, st[0].stats.delta)
    
    min_length = min(len(times), len(server_velocities), len(local_velocity_data), len(local_raw_data))
    times = times[:min_length]
    server_velocities = server_velocities[:min_length]
    local_velocity_data = np.array(local_velocity_data[:min_length])
    local_raw_data = np.array(local_raw_data[:min_length])

    if local_velocity_data.size == 0 or server_velocities.size == 0:
        logging.error("Local or server velocity data is empty after processing.")
        return

    correction_factor = np.mean(np.abs(server_velocities)) / np.mean(np.abs(local_velocity_data))
    local_velocity_data_corrected = local_velocity_data * correction_factor

    data_comparison_velocity = {
        "Time (s)": times,
        "Server Velocity (m/s)": server_velocities,
        "Local Velocity (m/s)": local_velocity_data_corrected
    }
    
    df_velocity = pd.DataFrame(data_comparison_velocity)
    logging.info("\n" + df_velocity.to_string())

    plt.figure(figsize=(12, 6))
    plt.plot(times, local_velocity_data_corrected, label='Local Velocity', color='green', alpha=0.7)
    plt.plot(times, server_velocities, label='Server Velocity', color='blue', alpha=0.7)

    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Velocity Comparison Between Server and Local')
    plt.legend()
    plt.show()

    if local_raw_data.size == 0:
        logging.error("Local raw data is empty after processing.")
        return

    try:
        st_raw = client.get_waveforms(network="AM", station=station, location="00", channel="EHZ", starttime=adjusted_start_time, endtime=end_time)
        server_raw_data = st_raw[0].data
        server_raw_data = server_raw_data[:min_length]
    except Exception as e:
        logging.error(f"No data available for request: {e}")
        return

    similarity_raw = calculate_similarity(server_raw_data, local_raw_data)

    logging.info(f"Similarity between server raw data and local raw data: {similarity_raw:.2f}%")

    data_comparison_raw = {
        "Time (s)": times,
        "Server Raw Data": server_raw_data,
        "Local Raw Data": local_raw_data
    }

    df_raw = pd.DataFrame(data_comparison_raw)
    logging.info("\n" + df_raw.to_string())

    plt.figure(figsize=(12, 6))
    plt.plot(times, server_raw_data, label='Server Raw Data', color='red', linestyle='-', linewidth=1.5, marker='o', markersize=2)
    plt.plot(times, local_raw_data, label='Local Raw Data', color='blue', linestyle='--', linewidth=1.5, marker='x', markersize=2)
    plt.xlabel('Time (s)')
    plt.ylabel('Raw Data')
    plt.title('Raw Data Comparison Between Server and Local')
    plt.legend()
    plt.show()

def main():
    station = "RECF8"
    start_time = UTCDateTime.now()
    current_time = time.time()

    duration = 60  # Collect data for 60 seconds
    
    inventory_path = "inventory.xml"  # Path to your locally saved inventory file

    seismograph = RealTimeSeismograph("192.168.1.73", 8888, inventory_path)
    logging.info(f"UTCDate: {start_time}")
    logging.info(f"Current timestamp: {current_time}")

    logging.info("Starting local data collection... ")
    seismograph.run(duration)

    adjusted_start_time = seismograph.adjusted_start_time
    logging.info(f"Adjusted start time: {adjusted_start_time}")

    logging.info("Starting server data fetch and comparison...")
    fetch_and_process_data(station, duration, seismograph.local_velocity_data, seismograph.local_raw_data, adjusted_start_time)
    logging.info("Data comparison process completed.")

if __name__ == "__main__":
    main()
