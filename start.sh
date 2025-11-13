#!/bin/bash

set -e

# Activate virtual environment
source venv/bin/activate

# Check for credentials
if [ ! -f "config/credentials.json" ]; then
    echo "Error: Google Drive credentials not found!"
    echo "Please download credentials.json from Google Cloud Console"
    echo "and place it in ./config/credentials.json"
    exit 1
fi

# Check for folder ID
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Copy .env.example to .env and configure it."
    echo ""
fi

echo "Starting Torrent-to-Drive..."
echo ""
echo "Access the web interface at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the application
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
