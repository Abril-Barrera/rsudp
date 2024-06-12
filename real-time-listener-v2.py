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
    def __init__(self, ip, port, threshold):
        self.ip = ip
        self.port = port
        self.threshold = threshold
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        logging.info(f"Listening for data on {self.ip}:{self.port}")
        self.C = -0.127
        logging.info(f"Empirical constant C: {self.C}")

    def process_data(self, data, correction_factor):
        try:
            #logging.debug(f"Received data of length: {len(data)} bytes")
            data_str = data.decode('utf-8')

            # Replace curly braces with square brackets to convert to a list format
            data_str = data_str.replace('{', '[').replace('}', ']')
            #logging.debug(f"Modified data string for evaluation: {data_str}")

            parsed_data = ast.literal_eval(data_str)
            seismic_readings = parsed_data[2:]
            #logging.debug(f"Seismic readings: {seismic_readings}")

            # Convert the seismic readings to a NumPy array
            np_data = np.array(seismic_readings, dtype=np.int32)

            # Create a Trace object from the NumPy array
            trace = obspy.Trace(data=np_data)
            st = obspy.Stream(traces=[trace])

            st.detrend("demean")
            st.detrend("linear")
            #logging.debug("Mean and linear trends removed")

            st.filter("bandpass", freqmin=0.1, freqmax=10.0)
            #logging.debug("Bandpass filter applied")

            st.integrate()
            #logging.debug("Integrated to convert displacement to velocity")

            velocity_data = st[0].data
            #logging.debug(f"Velocity data: {velocity_data}")

            corrected_velocity = velocity_data * correction_factor
            #logging.debug(f"Corrected velocity data: {corrected_velocity}")

            pgv = max(abs(corrected_velocity))
            #logging.debug(f"Peak Ground Velocity (PGV) calculated: {pgv}")

            magnitude = np.log10(pgv) + self.C
            logging.info(f"Estimated Richter Magnitude: {magnitude}")

            if magnitude >= self.threshold:
                self.trigger_alert(magnitude)
        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def trigger_alert(self, magnitude):
        #logging.warning(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")
        #print(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")
        pass

    def run(self, correction_factor):
        while True:
            buffer_size = 4096
            data, addr = self.sock.recvfrom(buffer_size)
            logging.debug(f"Received data from {addr}: {data}")
            self.process_data(data, correction_factor)

def main():
    ip = "192.168.1.73"
    port = 8888
    threshold = 0.0
    correction_factor = -0.00000013107801362631294
    logging.info("Starting local data collection...")
    seismograph = RealTimeSeismograph(ip, port, threshold)
    seismograph.run(correction_factor)

if __name__ == "__main__":
    main()
