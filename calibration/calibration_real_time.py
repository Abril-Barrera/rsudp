import socket
import obspy
import numpy as np
import logging
import ast

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class RealTimeSeismograph:
    def __init__(self, ip, port, threshold):
        self.ip = ip
        self.port = port
        self.threshold = threshold
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        logging.info(f"Listening for data on {self.ip}:{self.port}")

        # Calculate C using reference values
        reference_magnitude = 4.4
        reference_pgv = 0.004411  # m/s
        #self.C = reference_magnitude - np.log10(reference_pgv)
        self.C = 4.75
        logging.info(f"Empirical constant C calculated: {self.C}")

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

            channel = parsed_data[0]
            timestamp = parsed_data[1]
            seismic_readings = parsed_data[2:]

            # Log the parsed components
            logging.debug(f"Channel: {channel}")
            logging.debug(f"Timestamp: {timestamp}")
            logging.debug(f"Seismic readings: {seismic_readings}")

            # Convert the seismic readings to a NumPy array
            np_data = np.array(seismic_readings, dtype=np.int32)
            logging.debug(f"Converted data to NumPy array with shape: {np_data.shape}")

            # Create a Trace object from the NumPy array
            trace = obspy.Trace(data=np_data)
            st = obspy.Stream(traces=[trace])
            logging.debug("Stream object created")

            # Remove mean and linear trends
            st.detrend("demean")
            st.detrend("linear")
            logging.debug("Mean and linear trends removed")

            # Apply bandpass filter to isolate frequencies of interest
            st.filter("bandpass", freqmin=0.1, freqmax=10.0)
            logging.debug("Bandpass filter applied")

            # Integrate to convert displacement to velocity
            st.integrate()
            logging.debug("Integrated to convert displacement to velocity")

            # Log the velocity data
            velocity_data = st[0].data
            logging.debug(f"Velocity data: {velocity_data}")

            # Find Peak Ground Velocity (PGV)
            pgv = max(abs(velocity_data/10000000))
            logging.debug(f"Peak Ground Velocity (PGV) calculated: {pgv}")

            # Estimate Richter magnitude using the empirical relationship
            magnitude = np.log10(pgv) + self.C
            logging.info(f"Estimated Richter Magnitude: {magnitude}")

            # Trigger alert if magnitude exceeds threshold
            if magnitude >= self.threshold:
                self.trigger_alert(magnitude)
        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def trigger_alert(self, magnitude):
        logging.warning(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")
        print(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")

    def run(self):
        while True:
            data, addr = self.sock.recvfrom(4096)  # Adjust buffer size as needed
            logging.debug(f"Received data from {addr}: {data}")
            self.process_data(data)

if __name__ == "__main__":
    ip = "192.168.1.73"  # Computer's IP address
    port = 8888
    threshold = 0.0

    seismograph = RealTimeSeismograph(ip, port, threshold)
    seismograph.run()
