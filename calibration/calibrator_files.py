import numpy as np
import obspy
from obspy import read
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to adjust baseline
def adjust_baseline(trace):
    baseline = np.mean(trace.data)
    trace.data = trace.data - baseline
    logging.debug(f"Adjusted baseline: {baseline}")
    return trace

# Function to fetch and process data from MiniSEED files
def fetch_and_process_data(station_file, reference_station_file=None):
    # Read waveform data from MiniSEED file
    st = read(station_file)
    
    # Adjust baseline for each trace in the stream
    st = st.copy()  # Work on a copy to preserve the original data
    for trace in st:
        trace = adjust_baseline(trace)
    
    # Remove instrument response to get true ground motion velocity
    st.remove_response(output="VEL")
    
    # Plot the corrected data
    st.plot()
    
    # Compare with reference station if provided
    if reference_station_file:
        ref_st = read(reference_station_file)
        ref_st.remove_response(output="VEL")
        
        # Plot both streams for comparison
        st.plot()
        ref_st.plot()

# Main function
def main():
    # Example settings
    station_file = "RA9CD.mseed"  # Replace with your station MiniSEED file path
    reference_station_file = "R448E.mseed"  # Replace with your reference station MiniSEED file path, or None
    
    logging.info("Starting calibration process...")
    fetch_and_process_data(station_file, reference_station_file)
    logging.info("Calibration process completed.")

if __name__ == "__main__":
    main()
