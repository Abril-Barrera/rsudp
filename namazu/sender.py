import board
import busio
import time
import serial

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
usb_serial = serial.Serial('/dev/ttyUSB0', 9600)

def send_message(message):
    message_with_newline = message + '\n'
    uart.write(message_with_newline.encode())

while True:
    if usb_serial.in_waiting > 0:
        received_state = usb_serial.readline().decode().strip()
        send_message(received_state)
    time.sleep(0.01)