import board
import busio
import time
import pygame

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
pygame.mixer.init()

def play_sound(file):
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()

def receive_message():
    data = uart.readline()
    if data is not None:
        try:
            decoded = data.decode('utf-8').strip()
            return decoded
        except Exception as e:
            print(f"Failed to decode message: {e}")
            return None
    return None

first_received = False
last_received_time = time.time()

while True:
    message = receive_message()
    current_time = time.time()
    
    if message:
        print('Received: ', message)
        
        if not first_received:
            play_sound('connected.mp3')
            first_received = True
        if message == '2':
            play_sound('state2.mp3')
        elif message == '3':
            play_sound('state3.mp3')
        
        last_received_time = current_time

    if current_time - last_received_time > 60:
        play_sound('disconnected.mp3')
        first_received = False
        last_received_time = current_time
    
    time.sleep(0.01)
