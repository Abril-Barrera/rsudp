import board
import busio
import time
import usb_cdc

# Initialize UART
uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

# Initialize USB CDC
usb_serial = usb_cdc.data

def send_message(message):
    message_with_newline = message + '\n'
    uart.write(message_with_newline.encode())

def clear_buffer(serial_port):
    while serial_port.in_waiting > 0:
        serial_port.read(serial_port.in_waiting)

if usb_serial:
    while True:
        print('Running sender.py')
        if usb_serial.in_waiting > 0:
            received_state = usb_serial.readline().decode().strip()
            print('Received state: ', received_state)
            send_message(received_state)
            clear_buffer(usb_serial)
        time.sleep(0.01)
else:
    print('USB CDC data interface not available')
