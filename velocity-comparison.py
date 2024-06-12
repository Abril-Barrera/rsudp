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
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        self.local_velocity_data = []
        logging.info(f"Listening for data on {self.ip}:{self.port}")

    def process_data(self, data):
        try:
            #logging.debug(f"Received data of length: {len(data)} bytes")

            data_str = data.decode('utf-8')
            #logging.debug(f"Decoded data string: {data_str}")

            # Replace curly braces with square brackets to convert to a list format
            data_str = data_str.replace('{', '[').replace('}', ']')
            #logging.debug(f"Modified data string for evaluation: {data_str}")

            # Parse the data string
            parsed_data = ast.literal_eval(data_str)
            #logging.debug(f"Parsed data: {parsed_data}")

            seismic_readings = parsed_data[2:]

            # Log the parsed seismic readings
            #logging.debug(f"Seismic readings: {seismic_readings}")

            # Convert the seismic readings to a NumPy array
            np_data = np.array(seismic_readings, dtype=np.int32)
            #logging.debug(f"Converted data to NumPy array with shape: {np_data.shape}")

            # Create a Trace object from the NumPy array
            trace = obspy.Trace(data=np_data)
            st = obspy.Stream(traces=[trace])
            #logging.debug("Stream object created")

            # Remove mean and linear trends
            st.detrend("demean")
            st.detrend("linear")
            #logging.debug("Mean and linear trends removed")

            # Apply bandpass filter to isolate frequencies of interest
            st.filter("bandpass", freqmin=0.1, freqmax=10.0)
            #logging.debug("Bandpass filter applied")

            # Integrate to convert displacement to velocity
            st.integrate()
            #logging.debug("Integrated to convert displacement to velocity")

            # Log the velocity data
            velocity_data = st[0].data
            self.local_velocity_data.extend(velocity_data.tolist())
            #logging.debug(f"Velocity data: {velocity_data}")

        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def run(self):
        start_time = time.time()
        while time.time() - start_time < 60:  # Collect data for 1 minute
            data, addr = self.sock.recvfrom(4096)  # Adjust buffer size as needed
            #logging.debug(f"Received data from {addr}: {data}")
            self.process_data(data)
            elapsed_time = int(time.time() - start_time)
            logging.info(f"Seconds passed: {elapsed_time}")

def adjust_baseline(trace):
    baseline = np.mean(trace.data)
    trace.data = trace.data - baseline
    logging.debug(f"Adjusted baseline: {baseline}")
    return trace

def fetch_and_process_data(station, duration, local_velocity_data):
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
    
    # Fetch waveform data
    endtime = UTCDateTime.now()
    starttime = endtime - duration
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
    
    # Remove instrument response to get true ground motion velocity
    st.remove_response(inventory=inventory, output="VEL")
    
    times = np.arange(0, duration, st[0].stats.delta)
    velocities = st[0].data

    # Trim arrays to the same length
    min_length = min(len(times), len(velocities), len(local_velocity_data))
    times = times[:min_length]
    velocities = velocities[:min_length]
    local_velocity_data = np.array(local_velocity_data[:min_length])

    # Calculate the correction factor
    correction_factor = np.mean(velocities) / np.mean(local_velocity_data)
    corrected_local_velocity_data = local_velocity_data * correction_factor

    # Log the correction factor and the formula
    logging.info(f"Correction Factor: {correction_factor}")
    logging.info(f"Formula: corrected_local_velocity = local_velocity * {correction_factor}")

    # Prepare data for table
    data_comparison = {
        "Time (s)": times,
        "Server Velocity (m/s)": velocities,
        "Local Velocity (m/s)": local_velocity_data,
        "Corrected Local Velocity (m/s)": corrected_local_velocity_data,
    }
    
    # Convert to pandas DataFrame for better visualization
    df = pd.DataFrame(data_comparison)
    logging.info("\n" + df.to_string())  # Display the DataFrame in the logs

    # Plot both streams for comparison before and after correction
    plt.figure(figsize=(12, 6))
    plt.plot(times, velocities, label='Server Velocity', color='blue')
    plt.plot(times, local_velocity_data, label='Local Velocity (Before Correction)', color='green')
    plt.plot(times, corrected_local_velocity_data, label='Local Velocity (After Correction)', color='red')

    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Velocity Comparison Between Server and Local (Before and After Correction)')
    plt.legend()
    plt.show()

def main():
    station = "RA9CD"
    duration = 60 #seconds
    
    seismograph = RealTimeSeismograph("192.168.1.73", 8888)

    logging.info("Starting local data collection...")
    seismograph.run()

    logging.info("Starting server data fetch and comparison...")
    fetch_and_process_data(station, duration, seismograph.local_velocity_data)
    logging.info("Data comparison process completed.")

if __name__ == "__main__":
    main()
