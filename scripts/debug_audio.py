import sounddevice as sd
import numpy as np
import time

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    volume_norm = np.linalg.norm(indata) * 10
    print(f"|{'#' * int(volume_norm)}")

print("Testing default microphone...")
print(sd.query_devices(kind='input'))

try:
    # Open default stream
    with sd.InputStream(callback=audio_callback):
        print("Recording... Speak into microphone (Press Ctrl+C to stop)")
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped.")
except Exception as e:
    print(f"Error: {e}")
