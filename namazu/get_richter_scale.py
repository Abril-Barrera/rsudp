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

def trigger_alert(magnitude, threshold, alert_sound_path):
    if magnitude >= threshold and not pygame.mixer.music.get_busy():
        logging.warning(f"Alert! Estimated Magnitude: {magnitude:.2f}")
        pygame.mixer.music.load(alert_sound_path)
        pygame.mixer.music.play()

def save_to_file(data, filename):
    with open(filename, 'w') as file:
        file.write("Timestamp, Velocity, Richter Scale\n")
        for row in data:
            file.write(f"{row[0]}, {row[1]}, {row[2]}\n")
        magnitudes = [row[2] for row in data]
        file.write(f"MIN Richter Scale: {min(magnitudes):.2f}\n")
        file.write(f"MAX Richter Scale: {max(magnitudes):.2f}\n")

def process_data_realtime(sock, inventory, buffer_size, b_value, threshold, alert_sound_path):
    buffer = deque(maxlen=buffer_size)
    magnitudes = deque(maxlen=buffer_size)
    times = deque(maxlen=buffer_size)
    start_time = UTCDateTime.now()
    pygame.init()
    data_to_save = []
    filename = None

    while True:
        try:
            try:
                seismic_readings = read_data(sock)
            except Exception as e:
                logging.error(f"Error reading data: {e}")
                continue
            
            try:
                update_buffer(buffer, seismic_readings)
            except Exception as e:
                logging.error(f"Error updating buffer: {e}")
                continue
            
            try:
                trace = create_and_process_trace(buffer, inventory, start_time)
            except Exception as e:
                logging.error(f"Error creating and processing trace: {e}")
                continue
            
            try:
                pgv = calculate_pgv(trace.data)
            except Exception as e:
                logging.error(f"Error calculating PGV: {e}")
                continue
            
            try:
                magnitude = estimate_magnitude(pgv, b_value)
            except Exception as e:
                logging.error(f"Error estimating magnitude: {e}")
                continue
            
            try:
                trigger_alert(magnitude, threshold, alert_sound_path)
            except Exception as e:
                logging.error(f"Error triggering alert: {e}")
                continue
            
            try:
                current_time = UTCDateTime.now()
            except Exception as e:
                logging.error(f"Error getting current time: {e}")
                continue

            try:
                if magnitude >= threshold:
                    if not filename:
                        filename = f"{current_time.isoformat().replace(':', '-')}.txt"
                    data_to_save.append((current_time.isoformat(), pgv, magnitude))
                    save_to_file(data_to_save, filename)
                    logging.info(f"Logged magnitude {magnitude:.2f} at {current_time.isoformat()}")
            except Exception as e:
                logging.error(f"Error saving to file: {e}")
                continue

            try:
                elapsed_time = current_time - start_time
                logging.debug(f"Elapsed time: {elapsed_time}")
                times.append(elapsed_time)
                magnitudes.append(magnitude)
            except Exception as e:
                logging.error(f"Error calculating elapsed time or appending to lists: {e}")
                continue

            try:
                plot_magnitudes(times, magnitudes)
            except Exception as e:
                logging.error(f"Error plotting magnitudes: {e}")
                continue

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

def main():
    logging.info("----------------- Process started -----------------")
    pc_ip = "192.168.1.73"
    pc_port = 8888
    inventory_path = "namazu/inventory.xml"
    buffer_size_ms = 3000
    richter_b = 3.0
    richter_threshold = 4.0
    alert_sound_path = "namazu/alerta_cdmx.mp3"

    try:
        inventory_file = obspy.read_inventory(inventory_path)
        sock = initialize_socket(pc_ip, pc_port)
    except Exception as e:
        logging.error(f"Failed to initialize socket or read inventory: {e}")
        return

    logging.info("----------------- Starting real-time data processing -----------------")
    try:
        process_data_realtime(sock, inventory_file, buffer_size_ms, richter_b, richter_threshold, alert_sound_path)
    except Exception as e:
        logging.error(f"An error occurred during real-time data processing: {e}")

if __name__ == "__main__":
    main()
