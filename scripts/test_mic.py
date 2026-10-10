import sounddevice as sd
import numpy as np
import time

fs = 16000  # Sample rate
seconds = 3  # Duration of recording

print("Recording 3 seconds of audio in 3...")
time.sleep(1)
print("2...")
time.sleep(1)
print("1...")
time.sleep(1)
print("GO! Speak now!")

try:
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording finished.")

    print("Playing back...")
    sd.play(myrecording, fs)
    sd.wait()
    print("Playback finished. Did you hear yourself?")
except Exception as e:
    print(f"Error: {e}")
