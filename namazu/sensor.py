import os
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import socket
import obspy
import numpy as np
import logging
import ast
import matplotlib.pyplot as plt
from obspy import UTCDateTime
from collections import deque
import pygame
import csv
import serial
import yaml
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('pygame').setLevel(logging.WARNING)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def determine_state(richter_value, state_ranges):
    try: 
        logging.info(f"Determing state")

        if richter_value < state_ranges['state_0'][1]:
            return '0'
        elif state_ranges['state_1'][0] <= richter_value < state_ranges['state_1'][1]:
            return '1'
        elif state_ranges['state_2'][0] <= richter_value < state_ranges['state_2'][1]:
            return '2'
        elif state_ranges['state_3'][0] <= richter_value <= state_ranges['state_3'][1]:
            return '3'
        else:
            logging.error(f"State is not within correct range.")
    except Exception as e:
        logging.error(f"Failed to determine state.")

def send_state(ser, state):
    try:
        logging.info(f"Sending state")
        message_with_newline = state + '\n'
        logging.info(f"Writting state")
        ser.write(message_with_newline.encode())
        logging.info(f"Done wrritting state")
    except Exception as e:
        logging.error(f"Failed to send state.")

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
        if trace is None:
            raise
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
    try:
        ser = serial.Serial(config['emitter_serial_port'], config['emitter_baud_rate'])
    except Exception as e:
        logging.error(f"Error setting up serial connection: {e}")
    return ser

def process_seismic_data(buffer, inventory, start_time, pre_filt, config):
    try: 
        trace = create_and_process_trace(buffer, inventory, start_time, pre_filt, config)
        pgv = calculate_pgv(trace.data)
        magnitude = estimate_magnitude(pgv, config['richter_b'])
        return trace, pgv, magnitude
    except Exception as e:
        logging.error(f"Failed to process seismic_data: {e}")

def handle_plotting(times, magnitudes):
    plot_magnitudes(times, magnitudes)

def handle_state_transmission(ser, magnitude, config):
    try:
        logging.info(f"Handling state transmission")

        state = determine_state(magnitude, config['state_ranges'])
        send_state(ser, state)
        return state
    except Exception as e:
        logging.error(f"Failed to handle state transmission: {e}")


def process_data_realtime(sock, inventory, config):
    buffer = deque(maxlen=config['buffer_size_ms'])
    magnitudes = deque(maxlen=config['buffer_size_ms'])
    times = deque(maxlen=config['buffer_size_ms'])
    start_time = UTCDateTime.now()
    pygame.init()
    data_to_save = []
    ser = setup_serial_connection(config)
    if ser:
        logging.info(f"-: Serial connection set succesfully {ser}")

    while True:
        try:
            logging.info(f"-: STARTING CYCLE ")
            seismic_readings = read_data(sock)
            update_buffer(buffer, seismic_readings)
            trace, pgv, magnitude = process_seismic_data(buffer, inventory, start_time, config['pre_filt'], config)
            logging.info(f"-: Got trace pgv and magnitude")
            logging.info(f"-: Estimated magnitude {magnitude}")
            current_time = UTCDateTime.now()
            elapsed_time = current_time - start_time
            logging.debug(f"Elapsed time: {elapsed_time}")
            times.append(elapsed_time)
            magnitudes.append(magnitude)
            logging.info(f"-: Appended times succesfully")
            #handle_plotting(times, magnitudes)

            state = handle_state_transmission(ser, magnitude, config)
            logging.info(f"-: Handled state transmition")
            if state in config['csv_states']:
                logging.info(f"-: This shouldmnt appear")
                filename = f"{current_time.isoformat().replace(':', '-')}.csv"
                data_to_save.append((current_time.isoformat(), pgv, magnitude))
                save_to_csv(data_to_save, filename, config['csv_save_path'])

            logging.info(f"-: lAST ONE")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

def main():
    logging.info("----------------- Process started -----------------")

    with open('sensor_config.yaml', 'r') as file:
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
