import pigpio
import time

TX_PIN = 26  # GPIO pin for TX

# Initialize pigpio
pi = pigpio.pi()
print("sender.py")

if not pi.connected:
    exit()

pi.set_mode(TX_PIN, pigpio.OUTPUT)
baud = 9600

# Function to send data using bit-banging
def send_uart_data(pi, tx_pin, data, baud):
    pi.wave_clear()
    pi.wave_add_serial(tx_pin, baud, data)
    wave_id = pi.wave_create()
    pi.wave_send_once(wave_id)
    while pi.wave_tx_busy():
        time.sleep(0.01)  # Wait for the transmission to complete
    pi.wave_delete(wave_id)

# Send "hi" to the antenna
send_uart_data(pi, TX_PIN, b"hi", baud)
print("sent data")

# Stop pigpio
pi.stop()
