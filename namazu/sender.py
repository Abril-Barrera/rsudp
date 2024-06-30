import board
import busio
import time

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

def send_message(message):
    message_with_newline = message + '\n'
    uart.write(message_with_newline.encode())

while True:
    send_message("I am sending a message")
    time.sleep(1)
