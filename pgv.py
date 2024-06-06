import obspy
import numpy as np
import logging
from rsudp.client import Client

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class PGVAlert:
    def __init__(self, threshold):
        self.threshold = threshold  # Richter magnitude threshold
        logging.info(f"PGVAlert initialized with threshold: {threshold}")

    def process(self, data):
        try:
            logging.debug("Processing incoming data...")
            # Create a Stream object from the incoming data
            st = obspy.Stream(obspy.Trace(data))
            logging.debug("Stream object created")

            # Remove mean and linear trends
            st.detrend("demean")
            st.detrend("linear")
            logging.debug("Mean and linear trends removed")

            # Apply bandpass filter to isolate frequencies of interest
            st.filter("bandpass", freqmin=0.1, freqmax=20.0)
            logging.debug("Bandpass filter applied")

            # Integrate to convert displacement to velocity
            st.integrate()
            logging.debug("Integrated to convert displacement to velocity")

            # Find Peak Ground Velocity (PGV)
            pgv = max(abs(st[0].data))
            logging.debug(f"Peak Ground Velocity (PGV) calculated: {pgv}")

            # Convert PGV from m/s to cm/s
            pgv_cm_s = pgv * 100
            logging.debug(f"PGV converted to cm/s: {pgv_cm_s}")

            # Estimate Richter magnitude using the empirical relationship
            magnitude = np.log10(pgv_cm_s) + 2.4
            logging.info(f"Estimated Richter Magnitude: {magnitude}")

            # Trigger alert if magnitude exceeds threshold
            if magnitude >= self.threshold:
                self.trigger_alert(magnitude)
        except Exception as e:
            logging.error(f"Error processing data: {e}")

    def trigger_alert(self, magnitude):
        logging.warning(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")
        print(f"Earthquake detected! Estimated Richter Magnitude: {magnitude}")

# If running independently, test the code without the rsudp client
if __name__ == "__main__":
    try:
        # Simulate data for testing
        sample_data = np.random.randn(100)  # Replace with actual data format
        alert = PGVAlert(threshold=4.0)
        alert.process(sample_data)
    except Exception as e:
        logging.error(f"Error in standalone test: {e}")
