#!/bin/bash
# Start the Web UI using the virtual environment

cd /home/blob/Documents/jetson/router

if [ ! -d "venv" ]; then
    echo "Virtual environment not found! Please run 'python3 -m venv venv' first."
    exit 1
fi

echo "Starting Router Web Admin Interface on port 80 (requires sudo)..."
echo "You can view it from the Jetson by going to http://localhost"
echo "You can view it from connected devices by going to http://10.42.0.1 (or the Jetson's IP)"
echo "Press Ctrl+C to stop."

# We need sudo to bind to port 80
sudo ./venv/bin/python web_app.py
