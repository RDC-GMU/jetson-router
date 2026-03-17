#!/bin/bash
set -e

CURRENT_DIR=$(pwd)

echo "Installing system dependencies..."
sudo apt-get install -y python3-venv python3-pip wireless-tools

echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Verify venv was created successfully
if [ ! -f "venv/bin/pip" ]; then
    echo "ERROR: Virtual environment creation failed. Please check the output above."
    exit 1
fi

echo "Installing required Python packages..."
./venv/bin/pip install -r requirements.txt

echo "Installing rdc-router service..."
# Determine the absolute path of the current directory where the repo is cloned
CURRENT_DIR=$(pwd)

# Create a temporary copy of the service file to modify
cp rdc-router.service /tmp/rdc-router.service

# Use sed to replace the placeholder paths with the actual paths dynamically
sed -i "s|WorkingDirectory=.*|WorkingDirectory=${CURRENT_DIR}|g" /tmp/rdc-router.service
sed -i "s|ExecStart=.*|ExecStart=${CURRENT_DIR}/venv/bin/python ${CURRENT_DIR}/setup_router.py|g" /tmp/rdc-router.service

echo "Configuring service to run from: ${CURRENT_DIR}"
sudo mv /tmp/rdc-router.service /etc/systemd/system/rdc-router.service
sudo chmod 644 /etc/systemd/system/rdc-router.service

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling and starting the service..."
sudo systemctl enable rdc-router.service

sudo systemctl start rdc-router.service

echo "Service installation complete!"
echo "Check router & web UI status with: sudo systemctl status rdc-router.service"
