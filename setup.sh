#!/bin/bash

set -e

echo "========================================="
echo "Torrent-to-Drive Setup Script"
echo "========================================="

# Check if running on Debian/Ubuntu
if ! command -v apt-get &> /dev/null; then
    echo "Error: This script requires Debian/Ubuntu (apt-get not found)"
    exit 1
fi

echo ""
echo "Step 1: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    ca-certificates

# Install libtorrent via pip instead of apt (avoids package conflicts)
echo ""
echo "Step 1b: Installing libtorrent..."
pip3 install --user libtorrent

# Check if Node.js is already installed
echo ""
echo "Step 1c: Checking Node.js installation..."
if command -v node &> /dev/null; then
    echo "Node.js already installed: $(node --version)"
else
    echo "Installing Node.js from NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo ""
echo "Step 2: Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "Step 3: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 4: Creating necessary directories..."
mkdir -p data/torrents data/uploads config

echo ""
echo "Step 5: Setting up frontend..."
cd frontend
npm install
npm run build
cd ..

echo ""
echo "========================================="
echo "Setup completed successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Set up Google Drive API:"
echo "   - Go to https://console.cloud.google.com/"
echo "   - Create a new project or select existing"
echo "   - Enable Google Drive API"
echo "   - Create OAuth 2.0 credentials (Desktop app)"
echo "   - Download credentials as 'credentials.json'"
echo "   - Place it in ./config/credentials.json"
echo ""
echo "2. Configure settings:"
echo "   - Copy .env.example to .env"
echo "   - Set your DRIVE_FOLDER_ID in .env"
echo "   - (Optional) Adjust config/settings.yaml"
echo ""
echo "3. Start the application:"
echo "   - Run: ./start.sh"
echo "   - On first run, you'll authenticate with Google"
echo "   - Access UI at http://localhost:8000"
echo ""
