#!/bin/bash

echo "Stopping rdc-router service..."
sudo systemctl stop rdc-router.service

echo "Disabling rdc-router service so it does not start on boot..."
sudo systemctl disable rdc-router.service

echo "Removing the NetworkManager connection..."
/usr/bin/python3 /home/blob/Documents/jetson/router/teardown_router.py

echo "Hotspot turned off and service disabled."
echo "If you want to completely uninstall the service file, run:"
echo "sudo rm /etc/systemd/system/rdc-router.service && sudo systemctl daemon-reload"
