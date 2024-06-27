import board
import busio
import displayio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
import terminalio

# Liberar cualquier display anterior
displayio.release_displays()

# Configuración I2C
i2c = busio.I2C(board.GP7, board.GP6)

# Escanear dispositivos I2C
print("Escaneando I2C...")
while not i2c.try_lock():
    pass
try:
    devices = i2c.scan()
    if not devices:
        print("No se encontraron dispositivos I2C")
    else:
        print("Dispositivos I2C encontrados:", [hex(device) for device in devices])
finally:
    i2c.unlock()