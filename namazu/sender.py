import board
import busio
import time
import displayio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
import terminalio

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

def send_message(message):
    uart.write(message.encode())
    displayio.release_displays()
    i2c = busio.I2C(board.GP7, board.GP6)
    device_address = 0x3C
    display_bus = displayio.I2CDisplay(i2c, device_address=device_address)
    WIDTH = 128
    HEIGHT = 32
    display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)
    splash = displayio.Group()
    text = message
    text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF, x=10, y=10)
    splash.append(text_area)
    display.root_group = splash

while True:
    send_message("I am sending a message")
    time.sleep(1)
