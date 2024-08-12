import serial
import time

UART_DEVICE = "/dev/ttyS0"
BAUD_RATE = 9600

try:
    uart = serial.Serial(UART_DEVICE, BAUD_RATE, timeout=1)
    print("UART connection established.")
except Exception as e:
    print(f"Failed to establish UART connection: {e}")
    exit()

def send_uart_data(uart, data):
    try:
        uart.write(data)
        uart.flush()
        print("Data sent.")
    except Exception as e:
        print(f"Failed to send data over UART: {e}")

send_uart_data(uart, b"Antennas are working")
time.sleep(0.1) 
print("Sent data: 'A'")

uart.close()
