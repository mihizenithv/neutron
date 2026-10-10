import os
import zipfile
import urllib.request
from pathlib import Path

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "vosk-model-small-en-us-0.15"

def download_model():
    if MODEL_PATH.exists():
        print("Vosk model already exists.")
        return

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = MODEL_DIR / "model.zip"
    
    print(f"Downloading Vosk model from {MODEL_URL}...")
    urllib.request.urlretrieve(MODEL_URL, zip_path)
    
    print("Extracting model...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MODEL_DIR)
    
    # Rename if extracted folder has different name or just use as is
    # The zip usually contains the folder "vosk-model-small-en-us-0.15"
    
    os.remove(zip_path)
    print("Model downloaded and extracted.")

if __name__ == "__main__":
    download_model()
