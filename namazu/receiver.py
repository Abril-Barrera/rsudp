import board
import busio
import time
import audioio
import audiocore

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

def play_sound(filename):
    try:
        with open(filename, "rb") as file:
            wave = audiocore.WaveFile(file)
            with audioio.AudioOut(board.A0) as audio:  # Replace A0
                audio.play(wave)
                while audio.playing:
                    pass
    except Exception as e:
        print(f"Failed to play sound: {e}")

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
    if not first_received:
        play_sound('connected.wav')
        first_received = True

    message = receive_message()
    current_time = time.time()
    
    if message:
        print('Received: ', message)

        if message == '2':
            play_sound('state2.wav')
        elif message == '3':
            play_sound('state3.wav')
        
        last_received_time = current_time

    if current_time - last_received_time > 60:
        play_sound('disconnected.wav')
        first_received = False
        last_received_time = current_time
    
    time.sleep(0.01)
