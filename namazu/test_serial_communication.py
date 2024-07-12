import serial
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_serial_communication():
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        message = '0\n'
        logging.info(f"Writing to serial port: {message}")
        ser.write_timeout = 2  # Set write timeout to 2 seconds
        bytes_written = ser.write(message.encode())
        logging.info(f"Written {bytes_written} bytes to serial port")
        
        time.sleep(1)
        
        response = ser.read(100)  # Adjust buffer size if needed
        logging.info(f"Response from serial device: {response}")
        ser.close()
    except serial.SerialTimeoutException as e:
        logging.error(f"Serial write timeout: {e}")
    except Exception as e:
        logging.error(f"Serial communication test failed: {e}")

if __name__ == "__main__":
    test_serial_communication()
