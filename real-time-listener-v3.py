import socket
import obspy
import numpy as np
import logging
import ast

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class RealTimeSeismograph:
    def __init__(self, ip, port, threshold, inventory_path):
        self.ip = ip
        self.port = port
        self.threshold = threshold
        self.inventory = obspy.read_inventory(inventory_path)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        logging.info(f"Listening for data on {self.ip}:{self.port}")

        self.C = 2.9
        logging.info(f"Empirical constant C calculated: {self.C}")

    def process_data(self, data):
        try:
            logging.debug(f"Received data of length: {len(data)} bytes")

            data_str = data.decode('utf-8')
            logging.debug(f"Decoded data string: {data_str}")

            data_str = data_str.replace('{', '[').replace('}', ']')
            logging.debug(f"Modified data string for evaluation: {data_str}")

            parsed_data = ast.literal_eval(data_str)
            logging.debug(f"Parsed data: {parsed_data}")

            channel = parsed_data[0]
            timestamp = parsed_data[1]
            seismic_readings = parsed_data[2:]

            logging.debug(f"Channel: {channel}")
            logging.debug(f"Timestamp: {timestamp}")
            logging.debug(f"Seismic readings: {seismic_readings}")

            np_data = np.array(seismic_readings, dtype=np.int32)
            logging.debug(f"Converted data to NumPy array with shape: {np_data.shape}")

            trace = obspy.Trace(data=np_data)
            trace.stats.network = 'AM'
            trace.stats.station = 'RA9CD'
            trace.stats.location = '00'
            trace.stats.channel = 'EHZ'
            trace.stats.starttime = obspy.UTCDateTime(timestamp)
            
            st = obspy.Stream(traces=[trace])
            logging.debug("Stream object created")

            st.detrend("demean")
            st.detrend("linear")
            logging.debug("Mean and linear trends removed")

            st.filter("bandpass", freqmin=0.1, freqmax=10.0)
            logging.debug("Bandpass filter applied")

            st.attach_response(self.inventory)
            st.remove_response(output="VEL", pre_filt=[0.1, 0.2, 10.0, 20.0])
            logging.debug("Instrument response removed and converted to velocity")

            velocity_data = st[0].data
            logging.debug(f"Velocity data: {velocity_data}")

            pgv = max(abs(velocity_data))
            logging.debug(f"Peak Ground Velocity (PGV) calculated: {pgv}")

            magnitude = np.log10(pgv) + self.C
            logging.info(f"Estimated Richter Magnitude: {magnitude}")

            if magnitude >= self.threshold:
                self.trigger_alert(magnitude)
        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def trigger_alert(self, magnitude):
        logging.warning(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")
        print(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")

    def run(self):
        while True:
            data, addr = self.sock.recvfrom(4096)
            logging.debug(f"Received data from {addr}: {data}")
            self.process_data(data)

if __name__ == "__main__":
    ip = "192.168.1.73"
    port = 8888
    threshold = 0.0
    inventory_path = "inventory.xml"  # Path to your locally saved inventory file

    seismograph = RealTimeSeismograph(ip, port, threshold, inventory_path)
    seismograph.run()
