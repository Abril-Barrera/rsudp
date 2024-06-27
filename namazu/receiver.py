import board
import busio
import time

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

def receive_message():
    data = uart.readline()

    if data is not None:
        print('data is not none')
        print(data)
        decoded = data.decode('utf-8').strip()
        return decoded
    return None

while True:
    print('Listening to messasges... ')
    message = receive_message()

    if message:
        print('Received: ', message)

    time.sleep(1)
