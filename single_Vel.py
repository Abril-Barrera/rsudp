import socket
import obspy
import numpy as np
import logging
import ast
import matplotlib.pyplot as plt
from obspy import UTCDateTime
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

pre_filt = [0.01, 0.02, 20.0, 50.0]

def remove_response_and_convert_to_velocity(trace, inventory):
    trace.detrend("demean")
    trace.taper(0.05, type="cosine")
    trace.remove_response(inventory=inventory, output="VEL", pre_filt=pre_filt)
    return trace

def initialize_socket(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    logging.info(f"Listening for data on {ip}:{port}")
    return sock

def read_data(sock):
    data, addr = sock.recvfrom(4096)
    data_str = data.decode('utf-8').replace('{', '[').replace('}', ']')
    parsed_data = ast.literal_eval(data_str)
    seismic_readings = parsed_data[2:]
    return seismic_readings

def update_buffer(buffer, seismic_readings):
    buffer.extend(seismic_readings)

def create_and_process_trace(buffer, inventory, start_time):
    trace = obspy.Trace(data=np.array(buffer, dtype=np.int32))
    trace.stats.network = 'AM'
    trace.stats.station = 'RECF8'
    trace.stats.location = '00'
    trace.stats.channel = 'EHZ'
    trace.stats.starttime = start_time
    trace.stats.sampling_rate = 100.0
    trace = remove_response_and_convert_to_velocity(trace, inventory)
    return trace

def plot_trace(trace):
    plt.clf()
    plt.plot(trace.times(), trace.data, label='Processed Buffer')
    plt.xlabel('Time')
    plt.ylabel('Velocity (m/s)')
    plt.title('Real-time Seismograph')
    plt.pause(0.1)

def process_data_realtime(sock, inventory, buffer_size=1000):
    buffer = deque(maxlen=buffer_size)
    start_time = UTCDateTime.now()

    while True:
        seismic_readings = read_data(sock)
        update_buffer(buffer, seismic_readings)
        trace = create_and_process_trace(buffer, inventory, start_time)
        plot_trace(trace)

def main():
    logging.info("----------------- Process started -----------------")
    ip = "192.168.1.73"
    port = 8888
    inventory_path = "inventory.xml"
    inventory = obspy.read_inventory(inventory_path)
    sock = initialize_socket(ip, port)
    buffer_size = 1000

    logging.info("----------------- Starting real-time data processing -----------------")
    process_data_realtime(sock, inventory, buffer_size)

if __name__ == "__main__":
    main()
