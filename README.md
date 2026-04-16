# Jetson WiFi Router

This repository contains scripts to configure an NVIDIA Jetson (or any compatible Ubuntu system) as an internal WiFi router/Hotspot. This enables the Jetson to host an internal network where other devices can connect, retrieve an IP address, and communicate with each other or the Jetson itself.

This is especially useful for robotics or IoT applications where you want an isolated, self-hosted network directly from the Jetson.

## Features

- **Automated setup**: Automatically identifies the available WiFi interface.
- **NetworkManager integration**: Uses `nmcli` to reliably configure the hotspot.
- **Systemd Service**: Includes scripts to run the router automatically on startup.
- **Shared Network**: Utilizes IPv4 shared mode, providing DHCP and DNS for connected clients automatically (via `dnsmasq`).
- **Web Admin Dashboard**: Built-in Flask app on port 80 to view connected devices, change WiFi channels, manage static IPs, set custom DNS records, and configure port forwarding natively.

## Files Included

- `setup_router.py`: The core python script that uses `nmcli` to set up the NetworkManager `RDCJetson` connection.
- `teardown_router.py`: A script to gracefully turn off and delete the hotspot connection in NetworkManager.
- `rdc-router.service`: The systemd service configuration file.
- `install_service.sh`: A shell script to deploy, enable, and start the systemd service automatically.
- `stop_service.sh`: A shell script to stop and disable the service, along with removing the hotspot.

## Usage

### Option 1: Manual Run (Temporary / Testing)

You can manually run the script to initialize the router on demand:

```bash
chmod +x setup_router.py
./setup_router.py
```

By default, the script will create a network with:
- **SSID**: `RDCJetson`
- **Password**: `jetson123`

You can override these using arguments:
```bash
./setup_router.py --ssid "MyCustomNet" --password "supersecret" --name "MyCustomConnection"
```

### Option 2: Automatic Start on Boot (Service)

To ensure the router comes up automatically every time the Jetson powers on, install it as a system service.

```bash
chmod +x install_service.sh
./install_service.sh
```

*(This command uses `sudo` internally and may prompt for your password).*

You can check the status of the service at any time with:
```bash
systemctl status rdc-router.service
```

### Option 3: Turning it Off (Teardown)

If you need to stop the hotspot so the Jetson can connect to a normal WiFi network (like eduroam or a home network):

If you ran it manually, you can just run:
```bash
chmod +x teardown_router.py
./teardown_router.py
```

If you installed the service, use the stop script so it doesn't automatically turn back on when you reboot:
```bash
chmod +x stop_service.sh
./stop_service.sh
```

## How It Works

1. The `setup_router.py` script queries `nmcli` to find the physical WiFi interface (e.g., `wlan0`).
2. It deletes any existing NetworkManager connection with the designated name to prevent conflicts.
3. It creates an Access Point (AP) connection natively in NetworkManager.
4. When devices connect to the Jetson, they are automatically assigned an IP address (e.g., in the `10.42.0.x` range).
5. The Jetson itself will claim the `.1` address (e.g., `10.42.0.1`). 
6. Any device on this created network can communicate with the Jetson via `10.42.0.1`, and the Jetson can communicate with the devices using their assigned dynamic IP addresses.

## Web Admin Dashboard

The `setup_router.py` script automatically launches a Flask-based web interface on port 80. By navigating to `http://10.42.0.1` (or the Jetson's assigned IP) in your browser while connected to the hotspot, you can:

- **View Status**: See the current SSID, password, operating frequency, and connected devices.
- **Change Channels**: Dynamically switch the WiFi channel (e.g., 2.4GHz to 5GHz) to avoid interference.
- **Static IPs**: Assign static IP reservations to devices based on their MAC address (configured via `/etc/NetworkManager/dnsmasq-shared.d/jetson_static_ips.conf`).
- **Custom DNS**: Set local domain names (e.g., `uav.arc.co`) to resolve to specific IP addresses on the network using `dnsmasq` configurations.
- **Port Forwarding**: Automatically configure native Linux `iptables` rules to silently redirect traffic arriving on specific ports (e.g., forwarding port 80 to your backend app on port 8000) without needing extra proxy software.
