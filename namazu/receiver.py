import board
import busio
import time

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

def receive_message():
    data = uart.readline()

    if data is not None:
        try:
            decoded = data.decode('utf-8').strip()
            return decoded
        except Exception as e:
            print(f"Failed to decode message {e} ")
            return None
    return None

while True:
    print('Listening to messages... ')
    message = receive_message()

    if message:
        print('Received: ', message)

    time.sleep(1)
