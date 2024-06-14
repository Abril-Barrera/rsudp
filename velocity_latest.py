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

            trace = obspy.Trace(data=np_data)
            trace.stats.network = 'AM'
            trace.stats.station = 'RA9CD'
            trace.stats.location = '00'
            trace.stats.channel = 'EHZ'
            trace.stats.starttime = obspy.UTCDateTime(sensor_timestamp)

            st = obspy.Stream(traces=[trace])
            st.attach_response(self.inventory)
            print(' LOCAL CLEAN STREAM', st)

            # Improved filtering steps
            st.detrend("demean")
            st.taper(max_percentage=0.05, type='hann')  # Add a taper to smooth the edges

            # Adjust bandpass filter parameters for low sampling rate
            st.filter("bandpass", freqmin=0.1, freqmax=5.0, corners=4, zerophase=True)
            
            # Fine-tune the pre-filter for response removal
            pre_filt = [0.05, 0.1, 5.0, 10.0]
            st.remove_response(output="VEL", pre_filt=pre_filt)
            velocity_data = st[0].data
            self.local_velocity_data.extend(velocity_data.tolist())

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

def fetch_and_process_data(station, duration, local_velocity_data, adjusted_start_time):
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
    print(' SERVER CLEAN STREAM ', st)
    for trace in st:
        trace = adjust_baseline(trace)
    
    st.remove_response(inventory=inventory, output="VEL")
    server_velocities = st[0].data

    times = np.arange(0, duration, st[0].stats.delta)
    
    min_length = min(len(times), len(server_velocities), len(local_velocity_data))
    times = times[:min_length]
    server_velocities = server_velocities[:min_length]
    local_velocity_data = np.array(local_velocity_data[:min_length])

    # Calculate correction factor
    correction_factor = np.mean(np.abs(server_velocities)) / np.mean(np.abs(local_velocity_data))
    local_velocity_data_corrected = local_velocity_data * correction_factor

    data_comparison = {
        "Time (s)": times,
        "Server Velocity (m/s)": server_velocities,
        "Local Velocity (m/s)": local_velocity_data_corrected
    }
    
    df = pd.DataFrame(data_comparison)
    logging.info("\n" + df.to_string())

    plt.figure(figsize=(12, 6))
    plt.plot(times, local_velocity_data_corrected, label='Local Velocity', color='green')
    plt.plot(times, server_velocities, label='Server Velocity', color='blue')

    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Velocity Comparison Between Server and Local')
    plt.legend()
    plt.show()

def main():
    station = "RA9CD"
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
    fetch_and_process_data(station, duration, seismograph.local_velocity_data, adjusted_start_time)
    logging.info("Data comparison process completed.")

if __name__ == "__main__":
    main()
