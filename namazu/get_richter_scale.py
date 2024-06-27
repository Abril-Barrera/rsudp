import socket
import obspy
import numpy as np
import logging
import ast
import matplotlib.pyplot as plt
from obspy import UTCDateTime
from collections import deque
import pygame
import os
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

def remove_response_and_convert_to_velocity(trace, inventory, pre_filt):
    try:
        trace.detrend("demean")
        trace.taper(0.05, type="cosine")
        trace.remove_response(inventory=inventory, output="VEL", pre_filt=pre_filt)
    except Exception as e:
        logging.error(f"Error removing response and converting to velocity: {e}")
    return trace

def initialize_socket(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))
        logging.info(f"Listening for data on {ip}:{port}")
    except Exception as e:
        logging.error(f"Error initializing socket: {e}")
        raise
    return sock

def read_data(sock):
    try:
        data, addr = sock.recvfrom(4096)
        data_str = data.decode('utf-8').replace('{', '[').replace('}', ']')
        parsed_data = ast.literal_eval(data_str)
        seismic_readings = parsed_data[2:]
    except Exception as e:
        logging.error(f"Error reading data: {e}")
        raise
    return seismic_readings

def update_buffer(buffer, seismic_readings):
    try:
        buffer.extend(seismic_readings)
    except Exception as e:
        logging.error(f"Error updating buffer: {e}")
        raise

def create_and_process_trace(buffer, inventory, start_time, pre_filt):
    try:
        trace = obspy.Trace(data=np.array(buffer, dtype=np.int32))
        trace.stats.network = 'AM'
        trace.stats.station = 'RECF8'
        trace.stats.location = '00'
        trace.stats.channel = 'EHZ'
        trace.stats.starttime = start_time
        trace.stats.sampling_rate = 100.0
        trace = remove_response_and_convert_to_velocity(trace, inventory, pre_filt)
    except Exception as e:
        logging.error(f"Error creating and processing trace: {e}")
        raise
    return trace

def plot_magnitudes(times, magnitudes):
    try:
        plt.clf()
        plt.plot(times, magnitudes, label='Estimated Magnitude')
        plt.xlabel('Time')
        plt.ylabel('Richter Scale Magnitude')
        plt.title('Real-time Richter Scale Estimate')
        plt.legend()
        plt.pause(0.1)
    except Exception as e:
        logging.error(f"Error plotting magnitudes: {e}")
        raise

def calculate_pgv(velocity_data):
    try:
        pgv = np.max(np.abs(velocity_data))
    except Exception as e:
        logging.error(f"Error calculating PGV: {e}")
        raise
    return pgv

def estimate_magnitude(pgv, b_value):
    try:
        pgv_cm_s = pgv * 100
        magnitude = np.log10(pgv_cm_s) + b_value
    except Exception as e:
        logging.error(f"Error estimating magnitude: {e}")
        raise
    return magnitude

def trigger_alert(magnitude, threshold, alert_sound_path):
    try:
        if magnitude >= threshold and not pygame.mixer.music.get_busy():
            logging.warning(f"Alert! Estimated Magnitude: {magnitude:.2f}")
            pygame.mixer.music.load(alert_sound_path)
            pygame.mixer.music.play()
    except Exception as e:
        logging.error(f"Error triggering alert: {e}")
        raise

def save_to_csv(data, filename, save_path):
    try:
        filepath = os.path.join(save_path, filename)
        with open(filepath, 'w', newline='') as file:
            writer = csv.writer(file)
            magnitudes = [row[2] for row in data]
            writer.writerow(["MIN Richter Scale", min(magnitudes)])
            writer.writerow(["MAX Richter Scale", max(magnitudes)])
            writer.writerow(["Timestamp", "Velocity", "Richter Scale"])
            for row in data:
                writer.writerow(row)
        logging.info(f"Estimated Richter Scale Magnitude: {magnitudes[-1]:.2f}")
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")
        raise

def process_data_realtime(sock, inventory, buffer_size, b_value, threshold, alert_sound_path, pre_filt, save_path):
    buffer = deque(maxlen=buffer_size)
    magnitudes = deque(maxlen=buffer_size)
    times = deque(maxlen=buffer_size)
    start_time = UTCDateTime.now()
    pygame.init()
    data_to_save = []
    filename = None

    while True:
        try:
            seismic_readings = read_data(sock)
            update_buffer(buffer, seismic_readings)
            trace = create_and_process_trace(buffer, inventory, start_time, pre_filt)
            pgv = calculate_pgv(trace.data)
            magnitude = estimate_magnitude(pgv, b_value)
            trigger_alert(magnitude, threshold, alert_sound_path)

            current_time = UTCDateTime.now()
            if magnitude >= threshold:
                if not filename:
                    filename = f"{current_time.isoformat().replace(':', '-')}.csv"
                data_to_save.append((current_time.isoformat(), pgv, magnitude))
                save_to_csv(data_to_save, filename, save_path)

            elapsed_time = current_time - start_time
            logging.debug(f"Elapsed time: {elapsed_time}")
            times.append(elapsed_time)
            magnitudes.append(magnitude)

            plot_magnitudes(times, magnitudes)
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

def main():
    logging.info("----------------- Process started -----------------")
    pc_ip = "192.168.1.73"
    pc_port = 8888
    inventory_path = "namazu/inventory.xml"
    alert_sound_path = "namazu/alerta_cdmx.mp3"
    csv_save_path = "namazu/"
    buffer_size_ms = 3000
    richter_b = 0.0
    richter_threshold = 4.0
    pre_filt = [0.01, 0.02, 20.0, 50.0]

    try:
        inventory_file = obspy.read_inventory(inventory_path)
        sock = initialize_socket(pc_ip, pc_port)
    except Exception as e:
        logging.error(f"Failed to initialize socket or read inventory: {e}")
        return

    logging.info("----------------- Starting real-time data processing -----------------")
    try:
        process_data_realtime(sock, inventory_file, buffer_size_ms, richter_b, richter_threshold, alert_sound_path, pre_filt, csv_save_path)
    except Exception as e:
        logging.error(f"An error occurred during real-time data processing: {e}")

if __name__ == "__main__":
    main()
