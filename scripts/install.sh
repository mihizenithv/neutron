#!/bin/bash
# NEUTRON Installation Script
# Installs dependencies and sets up the system on Raspberry Pi 4

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║               NEUTRON Installation Script                     ║"
echo "║           Personal Assistant Robot Setup                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "❌ Do not run this script as root. Use a regular user with sudo privileges."
    exit 1
fi

# Check for Raspberry Pi
if [[ -f /proc/device-tree/model ]]; then
    MODEL=$(cat /proc/device-tree/model)
    echo "✓ Detected: $MODEL"
else
    echo "⚠ Not running on Raspberry Pi. Some features may not be available."
fi

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    portaudio19-dev \
    libsndfile1 \
    libatlas-base-dev \
    libasound2-dev \
    ffmpeg \
    git \
    curl \
    i2c-tools \
    libopenblas-dev

# Enable I2C for servo control (if on Pi)
if [[ -f /boot/config.txt ]]; then
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "🔧 Enabling I2C..."
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
        echo "⚠ Reboot required for I2C changes to take effect"
    fi
fi

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install optional Raspberry Pi packages
if [[ -f /proc/device-tree/model ]]; then
    echo "📦 Installing Raspberry Pi specific packages..."
    pip install RPi.GPIO adafruit-circuitpython-servokit || true
fi

# Create directories
echo "📁 Creating data directories..."
mkdir -p "$PROJECT_DIR/data/models"
mkdir -p "$PROJECT_DIR/data/audio"
mkdir -p "$PROJECT_DIR/data/memories"
mkdir -p "$PROJECT_DIR/logs"

# Copy example environment file
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "📄 Creating .env file from template..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠ Remember to edit .env with your API keys!"
fi

# Download models
echo ""
echo "📥 Downloading required models..."
bash "$SCRIPT_DIR/download_models.sh"

# Install systemd service (optional)
read -p "Install NEUTRON as a systemd service? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Installing systemd service..."
    sudo cp "$PROJECT_DIR/systemd/neutron.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    echo "✓ Service installed. Enable with: sudo systemctl enable neutron"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 Installation Complete! ✓                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run smoke test: ./scripts/smoke_test.sh"
echo "  3. Start NEUTRON: python -m server.main"
echo ""
