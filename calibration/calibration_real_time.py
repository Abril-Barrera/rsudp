import numpy as np
import obspy
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import logging
import time

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
    
    # Plot the corrected data
    st.plot()
    
    # Compare with reference station if provided
    if reference_station:
        try:
            ref_st = client.get_waveforms(network="AM", station=reference_station, location="00", channel="EHZ", starttime=starttime, endtime=endtime)
            ref_inventory = client.get_stations(network="AM", station=reference_station, level="response")
            ref_st.remove_response(inventory=ref_inventory, output="VEL")
            
            # Plot both streams for comparison
            st.plot()
            ref_st.plot()
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
