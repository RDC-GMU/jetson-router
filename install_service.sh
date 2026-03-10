#!/bin/bash

echo "Installing rdc-router service..."
sudo cp /home/blob/Documents/jetson/router/rdc-router.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/rdc-router.service

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling and starting the service..."
sudo systemctl enable rdc-router.service
sudo systemctl start rdc-router.service

echo "Service installation complete!"
echo "You can check the status with: sudo systemctl status rdc-router.service"
