import socket
import obspy
import numpy as np
import logging
import ast
import time
import matplotlib.pyplot as plt
from obspy.clients.fdsn import Client
from obspy import UTCDateTime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class RealTimeSeismograph:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        self.local_raw_data = []
        logging.info(f"Listening for data on {self.ip}:{self.port}")

    def process_data(self, data):
        try:
            logging.debug(f"Received data of length: {len(data)} bytes")

            data_str = data.decode('utf-8')
            logging.debug(f"Decoded data string: {data_str}")

            # Replace curly braces with square brackets to convert to a list format
            data_str = data_str.replace('{', '[').replace('}', ']')
            logging.debug(f"Modified data string for evaluation: {data_str}")

            # Parse the data string
            parsed_data = ast.literal_eval(data_str)
            logging.debug(f"Parsed data: {parsed_data}")

            seismic_readings = parsed_data[2:]

            # Log the parsed seismic readings
            logging.debug(f"Seismic readings: {seismic_readings}")

            # Convert the seismic readings to a NumPy array
            np_data = np.array(seismic_readings, dtype=np.int32)
            logging.debug(f"Converted data to NumPy array with shape: {np_data.shape}")

            # Store raw data
            self.local_raw_data.extend(np_data)
            logging.debug(f"Raw data: {np_data}")

        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def run(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:  # Collect data for specified duration
            data, addr = self.sock.recvfrom(4096)  # Adjust buffer size as needed
            logging.debug(f"Received data from {addr}: {data}")
            self.process_data(data)
            elapsed_time = int(time.time() - start_time)
            print(f"Seconds passed: {elapsed_time}")

def adjust_baseline(trace):
    baseline = np.mean(trace.data)
    trace.data = trace.data - baseline
    logging.debug(f"Adjusted baseline: {baseline}")
    return trace

def fetch_and_process_data(station, starttime, duration, local_raw_data):
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
    
    endtime = starttime + duration
    try:
        st = client.get_waveforms(network="AM", station=station, location="00", channel="EHZ", starttime=starttime, endtime=endtime)
    except Exception as e:
        logging.error(f"No data available for request: {e}")
        return
    
    # Fetch inventory (contains instrument response)
    try:
        inventory = client.get_stations(network="AM", station=station, level="response")
    except Exception as e:
        logging.error(f"Error fetching inventory: {e}")
        return
    
    # Adjust baseline for each trace in the stream
    st = st.copy()
    for trace in st:
        trace = adjust_baseline(trace)
    
    # Remove instrument response to get true ground motion displacement
    st.remove_response(inventory=inventory, output="DISP")

    times = np.arange(0, duration, st[0].stats.delta)
    displacements = st[0].data

    # Trim arrays to the same length
    min_length = min(len(times), len(displacements), len(local_raw_data))
    times = times[:min_length]
    displacements = displacements[:min_length]
    local_raw_data = local_raw_data[:min_length]

    # Calculate differences
    differences = local_raw_data - displacements
    min_diff = np.min(differences)
    max_diff = np.max(differences)

    # Plot both streams for comparison
    plt.figure(figsize=(12, 6))
    plt.plot(times, local_raw_data, label=f'Station RA9CD Local', color='green')
    plt.plot(times, displacements, label=f'Station RA9CD Server', color='blue')

    # Plot the differences
    plt.fill_between(times, local_raw_data, displacements, color='gray', alpha=0.5)
    plt.axhline(min_diff, color='red', linestyle='--', label=f'Min Diff: {min_diff:.6f}')
    plt.axhline(max_diff, color='orange', linestyle='--', label=f'Max Diff: {max_diff:.6f}')

    plt.xlabel('Time (s)')
    plt.ylabel('Displacement (m)')
    plt.title('Displacement comparison between RA9CD Server and RA9CD Local')
    plt.legend()
    plt.show()

def main():
    station = "RA9CD"
    duration = 60  # Duration in seconds (1 minute)
    starttime = UTCDateTime.now()

    seismograph = RealTimeSeismograph("192.168.1.73", 8888)

    logging.info("Starting local data collection...")
    seismograph.run(duration)

    logging.info("Starting server data fetch and comparison...")
    fetch_and_process_data(station, starttime, duration, seismograph.local_raw_data)
    logging.info("Data comparison process completed.")

if __name__ == "__main__":
    main()
