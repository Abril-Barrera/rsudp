import socket
import logging
import ast
import numpy as np
from scipy.integrate import cumtrapz

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class RealTimeSeismograph:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
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

            # Print the raw seismic readings
            print(f"Seismic readings: {seismic_readings}")

            # Assuming a sample rate of 100 Hz (10 ms between samples)
            sample_rate = 100.0  # Hz
            delta_time = 1.0 / sample_rate

            # Calculate velocity by integrating the seismic readings
            velocities = cumtrapz(seismic_readings, dx=delta_time, initial=0)
            times = np.arange(0, len(velocities) * delta_time, delta_time)

            for t, v in zip(times, velocities):
                print(f"Time: {t:.2f}s, Velocity: {v:.6f} m/s")

        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def run(self):
        while True:
            data, addr = self.sock.recvfrom(4096)  # Adjust buffer size as needed
            logging.debug(f"Received data from {addr}: {data}")
            self.process_data(data)

if __name__ == "__main__":
    ip = "192.168.1.73"  # Computer's IP address
    port = 8888

    seismograph = RealTimeSeismograph(ip, port)
    seismograph.run()
