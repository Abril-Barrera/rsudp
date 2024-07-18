import os
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
import yaml
import sys
import time
import pigpio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)
os.environ['SDL_AUDIODRIVER'] = 'dummy'

def setup_simulated_uart(tx_uart):
    try: 
        pi = pigpio.pi()
        if not pi.connected:
            exit()

        pi.set_mode(tx_uart, pigpio.OUTPUT)
        return pi
    except Exception as e:
        logging.error(f"Failed to setup simulated uart: {e}")

def send_uart_data(pi, tx_uart, data, baud_rate):
    try: 
        pi.wave_clear()
        pi.wave_add_serial(tx_uart, baud_rate, data)
        wave_id = pi.wave_create()
        pi.wave_send_once(wave_id)
        while pi.wave_tx_busy():
            time.sleep(0.01)
        pi.wave_delete(wave_id)
    except Exception as e:
        logging.error(f"Failed to transmit state through anthena TX: {e}")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def determine_state(richter_value, state_ranges):
    try: 
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
        logging.error(f"Failed to determine state: {e}")

def send_state(pi, state, tx_uart, baud_rate):
    try:
        send_uart_data(pi, tx_uart, state.encode(), baud_rate)
        logging.debug(f"Sent state to simulated UART: {state}")
    except Exception as e:
        logging.error(f"Failed to send state: {e}")

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
        sock.settimeout(5.0)
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
    except socket.timeout:
        logging.warning("Socket timeout occurred, no data received")
        return None
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
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")
        raise

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

def handle_state_transmission(pi, magnitude, config):
    try:
        state = determine_state(magnitude, config['state_ranges'])
        send_state(pi, state, config['tx_gpio_pin'], config['baud_rate'])
        return state
    except Exception as e:
        logging.error(f"Failed to handle state transmission: {e}")

def process_data_realtime(socket, inventory, config):
    buffer = deque(maxlen=config['buffer_size_ms'])
    magnitudes = deque(maxlen=config['buffer_size_ms'])
    times = deque(maxlen=config['buffer_size_ms'])
    start_time = UTCDateTime.now()
    pygame.init()
    data_to_save = []

    pi = setup_simulated_uart(config['tx_gpio_pin'])

    if pi:
        logging.info(f"-: Connection to anthena through TX was set successfully {pi}")

    while True:
        try:
            seismic_readings = read_data(socket)
            if seismic_readings is None:
                continue
            update_buffer(buffer, seismic_readings)
            trace, pgv, magnitude = process_seismic_data(buffer, inventory, start_time, config['pre_filt'], config)
            logging.info(f"Estimated Richter Magnitude {magnitude}")
            current_time = UTCDateTime.now()
            elapsed_time = current_time - start_time
            logging.debug(f"Elapsed time: {elapsed_time}")
            times.append(elapsed_time)
            magnitudes.append(magnitude)
            #handle_plotting(times, magnitudes)

            state = handle_state_transmission(pi, magnitude, config)
            if state in config['csv_states']:
                filename = f"{current_time.isoformat().replace(':', '-')}.csv"
                data_to_save.append((current_time.isoformat(), pgv, magnitude))
                save_to_csv(data_to_save, filename, config['csv_save_path'])

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
    
def main():
    logging.info("----------------- Process started -----------------")

    with open('sensor_config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    try:
        inventory_file = obspy.read_inventory(config['inventory_path'])
        socket = initialize_socket(config['pc_ip'], config['pc_port'])
    except Exception as e:
        logging.error(f"Failed to initialize socket or read inventory: {e}")
        return

    logging.info("----------------- Starting real-time data processing -----------------")
    try:
        process_data_realtime(socket, inventory_file, config)
    except Exception as e:
        logging.error(f"An error occurred during real-time data processing: {e}")

if __name__ == "__main__":
    main()
