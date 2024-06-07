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
    logging.debug(f"Adjusted baseline for {trace.id}: {baseline}")
    return trace

# Function to calibrate target data using reference data
def calibrate_data(target_trace, reference_trace):
    if len(target_trace.data) != len(reference_trace.data):
        raise ValueError("Target and reference traces must have the same length for calibration.")
    
    # Calculate the calibration offset
    calibration_offset = np.mean(reference_trace.data - target_trace.data)
    logging.debug(f"Calibration offset for {target_trace.id}: {calibration_offset}")

    # Apply the calibration offset
    target_trace.data = target_trace.data + calibration_offset

    # Log the mean and standard deviation of the target and reference traces
    logging.debug(f"Mean and std before calibration for {target_trace.id}: {np.mean(target_trace.data)}, {np.std(target_trace.data)}")
    logging.debug(f"Mean and std for {reference_trace.id}: {np.mean(reference_trace.data)}, {np.std(reference_trace.data)}")
    logging.debug(f"Mean and std after calibration for {target_trace.id}: {np.mean(target_trace.data)}, {np.std(target_trace.data)}")

    return target_trace

# Function to fetch and process data from MiniSEED files
def fetch_and_process_data(target_station_file, reference_station_file):
    # Read waveform data from MiniSEED files
    target_stream = read(target_station_file)
    reference_stream = read(reference_station_file)
    
    # Adjust baseline for each trace in the target and reference streams
    target_stream = target_stream.copy()  # Work on a copy to preserve the original data
    reference_stream = reference_stream.copy()  # Work on a copy to preserve the original data

    for target_trace, reference_trace in zip(target_stream, reference_stream):
        target_trace = adjust_baseline(target_trace)
        reference_trace = adjust_baseline(reference_trace)
        
        # Calibrate the target trace using the reference trace
        target_trace = calibrate_data(target_trace, reference_trace)

    # Plot the calibrated target data and the reference data
    logging.info("Plotting calibrated target data...")
    target_stream.plot()
    logging.info("Plotting reference data...")
    reference_stream.plot()

# Main function
def main():
    # Example settings
    target_station_file = r"C:\Users\abril\OneDrive\Documents\GitHub\rsudp\calibration\RA9CD.mseed"  # Replace with your target station MiniSEED file path
    reference_station_file = r"C:\Users\abril\OneDrive\Documents\GitHub\rsudp\calibration\R448E.mseed"  # Replace with your reference station MiniSEED file path
    
    logging.info("Starting calibration process...")
    fetch_and_process_data(target_station_file, reference_station_file)
    logging.info("Calibration process completed.")

if __name__ == "__main__":
    main()
