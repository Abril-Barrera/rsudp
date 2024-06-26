import socket
import obspy
import numpy as np
import logging
import ast
import matplotlib.pyplot as plt
from obspy import UTCDateTime
from collections import deque
import winsound

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

def plot_magnitudes(times, magnitudes):
    plt.clf()
    plt.plot(times, magnitudes, label='Estimated Magnitude')
    plt.xlabel('Time')
    plt.ylabel('Richter Scale Magnitude')
    plt.title('Real-time Richter Scale Estimate')
    plt.legend()
    plt.pause(0.1)

def calculate_pgv(velocity_data):
    return np.max(np.abs(velocity_data))

def estimate_magnitude(pgv, b_value):
    pgv_cm_s = pgv * 100
    magnitude = np.log10(pgv_cm_s) + b_value
    return magnitude

def trigger_alert(magnitude, threshold, duration, freq):
    if magnitude >= threshold:
        logging.warning(f"Alert! Estimated Magnitude: {magnitude:.2f}")
        winsound.Beep(freq, duration)

def process_data_realtime(sock, inventory, buffer_size, b_value, threshold, duration, freq):
    buffer = deque(maxlen=buffer_size)
    magnitudes = deque(maxlen=buffer_size)
    times = deque(maxlen=buffer_size)
    start_time = UTCDateTime.now()

    while True:
        seismic_readings = read_data(sock)
        update_buffer(buffer, seismic_readings)
        trace = create_and_process_trace(buffer, inventory, start_time)
        pgv = calculate_pgv(trace.data)
        magnitude = estimate_magnitude(pgv, b_value)
        trigger_alert(magnitude, threshold, duration, freq)
        current_time = UTCDateTime.now()
        times.append(current_time - start_time)
        magnitudes.append(magnitude)
        plot_magnitudes(times, magnitudes)

def main():
    logging.info("----------------- Process started -----------------")
    pc_ip = "192.168.1.73"
    pc_port = 8888
    inventory_path = "namazu/inventory.xml"
    buffer_size_ms = 3000
    richter_b = 3.0
    richter_threshold = 4.0
    alert_duration_ms = 5000
    alert_freq_hz = 500
    
    inventory_file = obspy.read_inventory(inventory_path)
    socket = initialize_socket(pc_ip, pc_port)

    logging.info("----------------- Starting real-time data processing -----------------")
    process_data_realtime(socket, inventory_file, buffer_size_ms, richter_b, richter_threshold, alert_duration_ms, alert_freq_hz)

if __name__ == "__main__":
    main()
