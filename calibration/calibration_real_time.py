import numpy as np
import obspy
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import logging
import time
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def adjust_baseline(trace):
    baseline = np.mean(trace.data)
    trace.data = trace.data - baseline
    logging.debug(f"Adjusted baseline: {baseline}")
    return trace

def fetch_and_process_data(station, starttime, duration, reference_station=None):
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
    
    # Remove instrument response to get true ground motion velocity
    st.remove_response(inventory=inventory, output="VEL")
    
    times = np.arange(0, duration, st[0].stats.delta)
    velocities = st[0].data

    # Compare with reference station if provided
    if reference_station:
        try:
            ref_st = client.get_waveforms(network="AM", station=reference_station, location="00", channel="EHZ", starttime=starttime, endtime=endtime)
            ref_inventory = client.get_stations(network="AM", station=reference_station, level="response")
            ref_st.remove_response(inventory=ref_inventory, output="VEL")
            
            ref_times = np.arange(0, duration, ref_st[0].stats.delta)
            ref_velocities = ref_st[0].data

            # Trim arrays to the same length
            min_length = min(len(times), len(ref_times), len(velocities), len(ref_velocities))
            times = times[:min_length]
            ref_times = ref_times[:min_length]
            velocities = velocities[:min_length]
            ref_velocities = ref_velocities[:min_length]

            # Plot both streams for comparison
            plt.figure(figsize=(12, 6))
            plt.plot(times, velocities, label=f'Station {station}', color='blue')
            plt.plot(ref_times, ref_velocities, label=f'Reference Station {reference_station}', color='green')
            
            # Calculate and plot the difference
            differences = velocities - ref_velocities
            min_diff = np.min(differences)
            max_diff = np.max(differences)
            
            plt.fill_between(times, velocities, ref_velocities, color='gray', alpha=0.5)
            plt.axhline(min_diff, color='red', linestyle='--', label=f'Min Diff: {min_diff:.6f}')
            plt.axhline(max_diff, color='orange', linestyle='--', label=f'Max Diff: {max_diff:.6f}')
            
            plt.xlabel('Time (s)')
            plt.ylabel('Velocity (m/s)')
            plt.title('Velocity comparison between RA9CD-R448E stations during the 7th June earthquake')
            plt.legend()
            plt.show()
            
        except Exception as e:
            logging.error(f"Error fetching data for reference station: {e}")

def main():
    station = "RA9CD"
    reference_station = "R448E"
    starttime_str = "2024-06-07T19:00:00"
    starttime = UTCDateTime(starttime_str)
    duration = 7200 
    
    logging.info("Starting calibration process...")
    fetch_and_process_data(station, starttime, duration, reference_station)
    logging.info("Calibration process completed.")

if __name__ == "__main__":
    main()
