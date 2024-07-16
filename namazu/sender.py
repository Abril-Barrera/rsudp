import board
import busio
import time
import usb_cdc
import queue

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
usb_serial = usb_cdc.data
write_queue = queue.Queue(maxsize=1024) #64bytes x 4

def send_message(message):
    message_with_newline = message + '\n'
    try:
        write_queue.put_nowait(message_with_newline.encode())
    except queue.Full:
        print("Warning: Write queue is full. Message dropped.")

def read_from_usb():
    try:
        if usb_serial and usb_serial.in_waiting > 0:
            return usb_serial.readline().decode().strip()
    except Exception as e:
        print(f"Failed to read from USB serial: {e}")
    return None

def write_to_uart():
    try:
        if not write_queue.empty():
            message = write_queue.get_nowait()
            uart.write(message)
    except Exception as e:
        print(f"Failed to write to UART: {e}")

if usb_serial:
    while True:
        try:
            received_state = read_from_usb()
            if received_state:
                print('Received state:', received_state)
                send_message(received_state)
            write_to_uart()

            #time.sleep(0.01)  # Throttle the loop to manage CPU usage
        except Exception as e:
            print(f"Error in main loop: {e}")
else:
    print('USB CDC data interface not available')
