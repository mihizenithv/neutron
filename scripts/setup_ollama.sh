#!/bin/bash
# NEUTRON Ollama Setup Script
# Installs Ollama and pulls recommended models for local LLM inference

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║               NEUTRON Ollama Setup                            ║"
echo "║           Local LLM for Monitoring & Emotions                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if running on Linux/macOS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    echo "⚠ Windows detected. Please install Ollama manually from: https://ollama.com/download"
    echo "After installation, run: ollama pull llama3.2:1b"
    exit 0
fi

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is already installed"
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
    echo "  Version: $OLLAMA_VERSION"
else
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
fi

# Start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚀 Starting Ollama service..."
    ollama serve &
    sleep 3
fi

# Determine best model based on available RAM
TOTAL_RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "4")
echo "📊 Detected RAM: ${TOTAL_RAM_GB}GB"

if [[ $TOTAL_RAM_GB -ge 8 ]]; then
    MODEL="mistral:7b"
    echo "💡 Recommended model for 8GB+ RAM: $MODEL"
elif [[ $TOTAL_RAM_GB -ge 4 ]]; then
    MODEL="llama3.2:3b"
    echo "💡 Recommended model for 4GB RAM: $MODEL"
else
    MODEL="llama3.2:1b"
    echo "💡 Recommended model for low RAM: $MODEL"
fi

# Pull the model
echo ""
echo "📥 Pulling model: $MODEL"
echo "   This may take several minutes..."
ollama pull $MODEL

# Also pull a tiny model for fallback
echo ""
echo "📥 Pulling fallback model: llama3.2:1b"
ollama pull llama3.2:1b

# Test the model
echo ""
echo "🧪 Testing Ollama..."
RESPONSE=$(ollama run $MODEL "Say 'NEUTRON online' in 5 words or less" 2>/dev/null || echo "Test failed")
echo "   Response: $RESPONSE"

# Update .env if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    echo ""
    echo "📝 Updating .env file..."
    
    # Enable Ollama
    if grep -q "^OLLAMA_ENABLED=" "$ENV_FILE"; then
        sed -i 's/^OLLAMA_ENABLED=.*/OLLAMA_ENABLED=true/' "$ENV_FILE"
    else
        echo "OLLAMA_ENABLED=true" >> "$ENV_FILE"
    fi
    
    # Set model
    if grep -q "^OLLAMA_MODEL=" "$ENV_FILE"; then
        sed -i "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$MODEL/" "$ENV_FILE"
    else
        echo "OLLAMA_MODEL=$MODEL" >> "$ENV_FILE"
    fi
    
    echo "✓ .env updated with OLLAMA_ENABLED=true and OLLAMA_MODEL=$MODEL"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 Ollama Setup Complete! ✓                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Model installed: $MODEL"
echo "Ollama API URL: http://localhost:11434"
echo ""
echo "To test manually:"
echo "  ollama run $MODEL 'Hello!'"
echo ""
echo "To use with NEUTRON, ensure .env has:"
echo "  OLLAMA_ENABLED=true"
echo "  OLLAMA_MODEL=$MODEL"
