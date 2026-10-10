#!/bin/bash
# NEUTRON Model Download Script
# Downloads Vosk and Piper models for offline speech processing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_DIR/data/models"

echo "📥 NEUTRON Model Downloader"
echo "=========================="
echo ""

mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Vosk STT Model (small English)
VOSK_MODEL="vosk-model-small-en-us-0.15"
VOSK_URL="https://alphacephei.com/vosk/models/$VOSK_MODEL.zip"

if [[ ! -d "$VOSK_MODEL" ]]; then
    echo "📦 Downloading Vosk STT model..."
    curl -L -o "$VOSK_MODEL.zip" "$VOSK_URL"
    unzip -q "$VOSK_MODEL.zip"
    rm "$VOSK_MODEL.zip"
    echo "✓ Vosk model installed: $VOSK_MODEL"
else
    echo "✓ Vosk model already exists: $VOSK_MODEL"
fi

# Piper TTS Model (en_US-lessac-medium)
PIPER_VOICE="en_US-lessac-medium"
PIPER_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium"

mkdir -p "piper"
cd "piper"

if [[ ! -f "$PIPER_VOICE.onnx" ]]; then
    echo "📦 Downloading Piper TTS model..."
    curl -L -o "$PIPER_VOICE.onnx" "$PIPER_URL/en_US-lessac-medium.onnx"
    curl -L -o "$PIPER_VOICE.onnx.json" "$PIPER_URL/en_US-lessac-medium.onnx.json"
    echo "✓ Piper voice installed: $PIPER_VOICE"
else
    echo "✓ Piper voice already exists: $PIPER_VOICE"
fi

cd "$MODELS_DIR"

# openWakeWord models
echo "📦 Downloading openWakeWord models..."
python3 -c "
import os
try:
    from openwakeword.model import Model
    print('✓ openWakeWord models will be downloaded on first use')
except ImportError:
    print('⚠ openWakeWord not installed, skipping')
" 2>/dev/null || echo "⚠ Could not check openWakeWord models"

# Sentence Transformers (for embeddings)
echo "📦 Pre-caching sentence-transformers model..."
python3 -c "
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print('✓ Embeddings model cached')
except Exception as e:
    print(f'⚠ Could not cache embeddings model: {e}')
" 2>/dev/null || echo "⚠ Could not cache embeddings model"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 Models Downloaded! ✓                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Models location: $MODELS_DIR"
ls -lh "$MODELS_DIR"
