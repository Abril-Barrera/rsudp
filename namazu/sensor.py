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
import serial
import time
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

def determine_state(richter_value, state_ranges):
    if state_ranges['state_1'][0] <= richter_value < state_ranges['state_1'][1]:
        return '1'
    elif state_ranges['state_2'][0] <= richter_value < state_ranges['state_2'][1]:
        return '2'
    elif state_ranges['state_3'][0] <= richter_value <= state_ranges['state_3'][1]:
        return '3'

def send_state(ser, state):
    ser.write(state.encode())

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

def create_and_process_trace(buffer, inventory, start_time, pre_filt, config):
    try:
        trace = obspy.Trace(data=np.array(buffer, dtype=np.int32))
        trace.stats.network = config['network']
        trace.stats.station = config['station']
        trace.stats.location = config['location']
        trace.stats.channel = config['channel']
        trace.stats.starttime = start_time
        trace.stats.sampling_rate = config['sampling_rate']
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

def setup_serial_connection(config):
    return serial.Serial(config['emitter_serial_port'], config['emitter_baud_rate'])

def process_seismic_data(buffer, inventory, start_time, pre_filt, config):
    trace = create_and_process_trace(buffer, inventory, start_time, pre_filt, config)
    pgv = calculate_pgv(trace.data)
    magnitude = estimate_magnitude(pgv, config['richter_b'])
    return magnitude, trace

def handle_alerts(magnitude, config):
    trigger_alert(magnitude, config['richter_threshold'], config['alert_sound_path'])

def handle_plotting(times, magnitudes):
    plot_magnitudes(times, magnitudes)

def handle_state_transmission(ser, magnitude, config, last_data_time):
    state = determine_state(magnitude, config['state_ranges'])
    send_state(ser, state)
    return time.time()

def process_data_realtime(sock, inventory, config):
    buffer = deque(maxlen=config['buffer_size_ms'])
    magnitudes = deque(maxlen=config['buffer_size_ms'])
    times = deque(maxlen=config['buffer_size_ms'])
    start_time = UTCDateTime.now()
    pygame.init()
    data_to_save = []
    filename = None
    ser = setup_serial_connection(config)
    if not ser:
        return

    last_data_time = time.time()

    while True:
        try:
            seismic_readings = read_data(sock)
            update_buffer(buffer, seismic_readings)
            magnitude, trace = process_seismic_data(buffer, inventory, start_time, config['pre_filt'], config)
            handle_alerts(magnitude, config)

            current_time = UTCDateTime.now()
            if magnitude >= config['richter_threshold']:
                if not filename:
                    filename = f"{current_time.isoformat().replace(':', '-')}.csv"
                data_to_save.append((current_time.isoformat(), pgv, magnitude))
                save_to_csv(data_to_save, filename, config['csv_save_path'])

            elapsed_time = current_time - start_time
            logging.debug(f"Elapsed time: {elapsed_time}")
            times.append(elapsed_time)
            magnitudes.append(magnitude)

            handle_plotting(times, magnitudes)

            last_data_time = handle_state_transmission(ser, magnitude, config, last_data_time)
        except socket.timeout:
            if time.time() - last_data_time > config['state_0_timeout']:
                send_state(ser, '0')
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

def main():
    logging.info("----------------- Process started -----------------")

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    try:
        inventory_file = obspy.read_inventory(config['inventory_path'])
        sock = initialize_socket(config['pc_ip'], config['pc_port'])
    except Exception as e:
        logging.error(f"Failed to initialize socket or read inventory: {e}")
        return

    logging.info("----------------- Starting real-time data processing -----------------")
    try:
        process_data_realtime(sock, inventory_file, config)
    except Exception as e:
        logging.error(f"An error occurred during real-time data processing: {e}")

if __name__ == "__main__":
    main()
