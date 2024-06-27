import board
import busio

uart = busio.UART(board.GP0, board.GP1, baudrate=9600, timeout=0.1)

def receive_message():
    data = uart.read(32)
    if data is not None:
        return data.decode('utf-8').strip()
    return None

while True:
    message = receive_message()
    if message:
        print("Received:", message)
