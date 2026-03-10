#!/usr/bin/env python
import subprocess
import sys
import time
import argparse
import re
from flask import Flask, render_template

def run_command(command, check=True):
    try:
        result = subprocess.run(command, check=check, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr.strip()}")
        if check:
            sys.exit(1)
        return None

def get_wifi_interface():
    output = run_command("nmcli -t -f DEVICE,TYPE d", check=False)
    if output:
        for line in output.split('\n'):
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == 'wifi':
                return parts[0]
    return None

def setup_hotspot(ssid, password, con_name):
    iface = get_wifi_interface()
    if not iface:
        print("No WiFi interface found on this system.")
        print("Please ensure your WiFi card is connected and recognized.")
        sys.exit(1)
        
    print(f"Found WiFi interface: {iface}")
    
    con_output = run_command("nmcli -t -f NAME con show", check=False)
    if con_output:
        for line in con_output.split('\n'):
            if line == con_name:
                print(f"Removing existing connection: {line}")
                run_command(f"nmcli con delete '{line}'", check=False)

    print(f"Setting up WiFi hotspot '{con_name}' with SSID: '{ssid}'...")
    
    print("Creating the hotspot connection...")
    run_command(f"nmcli con add type wifi ifname {iface} con-name '{con_name}' autoconnect yes ssid '{ssid}'")
    
    run_command(f"nmcli con modify '{con_name}' 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared")
    
    if password:
        run_command(f"nmcli con modify '{con_name}' wifi-sec.key-mgmt wpa-psk")
        run_command(f"nmcli con modify '{con_name}' wifi-sec.psk '{password}'")
    
    print("Activating the hotspot...")
    run_command(f"nmcli con up '{con_name}'")
    
    time.sleep(2)
    
    ip_output = run_command(f"ip -4 addr show {iface} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}'", check=False)
    
    print("\n" + "="*50)
    print("Hotspot setup complete!")
    print(f"Connection Name: {con_name}")
    print(f"SSID: {ssid}")
    print(f"Password: {password}")
    if ip_output:
        print(f"Jetson's IP Address on the internal network: {ip_output}")
    print("="*50)

# --- FLASK WEB APP ---

app = Flask(__name__)

def get_router_info():
    iface = get_wifi_interface()
    info = {
        'interface': iface,
        'ip': 'Unknown',
        'ssid': 'Unknown',
        'password': 'Unknown',
        'status': 'Inactive'
    }
    if iface:
        try:
            ip_out = subprocess.check_output(f"ip -4 addr show {iface} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}'", shell=True, text=True)
            if ip_out:
                info['ip'] = ip_out.strip()
            
            con_out = subprocess.check_output(f"nmcli -t -f GENERAL.CONNECTION dev show {iface}", shell=True, text=True)
            con_name = con_out.split(':')[1].strip()
            if con_name and con_name != '--':
                info['ssid'] = con_name
                info['status'] = 'Active'
                try:
                    actual_ssid = subprocess.check_output(f"nmcli -t -f 802-11-wireless.ssid connection show '{con_name}'", shell=True, text=True).strip()
                    if actual_ssid and ':' in actual_ssid:
                        info['ssid'] = actual_ssid.split(':', 1)[1].strip()
                except Exception:
                    pass
                try:
                    psk = subprocess.check_output(f"nmcli -s -g 802-11-wireless-security.psk connection show '{con_name}'", shell=True, text=True).strip()
                    if psk:
                        info['password'] = psk
                    else:
                        info['password'] = 'None (Open Network)'
                except Exception:
                    info['password'] = 'Unknown'
        except Exception:
            pass
    return info

import glob

def get_connected_devices():
    iface = get_wifi_interface()
    devices = {}
    if iface:
        lease_files = glob.glob(f"/var/lib/NetworkManager/dnsmasq-*.leases") + \
                      glob.glob(f"/var/run/nm-dnsmasq-*.leases") + \
                      glob.glob(f"/var/lib/misc/dnsmasq.leases")
        for lf in lease_files:
            try:
                with open(lf, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            mac = parts[1].upper()
                            ip = parts[2]
                            hostname = parts[3]
                            if hostname == '*':
                                hostname = 'Unknown'
                            devices[ip] = {'ip': ip, 'mac': mac, 'state': 'Standby (DHCP Lease)'}
            except Exception:
                pass

        try:
            output = subprocess.check_output(f"ip neigh show dev {iface}", shell=True, text=True)
            for line in output.split('\n'):
                if not line.strip() or 'FAILED' in line or 'INCOMPLETE' in line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    ip = parts[0]
                    mac = parts[4].upper()
                    state = parts[-1]
                    if ip in devices:
                        devices[ip]['state'] = f"Active ({state})"
                    else:
                        devices[ip] = {'ip': ip, 'mac': mac, 'state': f"Active ({state})"}
        except Exception:
            pass
    return list(devices.values())

@app.route('/')
def index():
    router_info = get_router_info()
    devices = get_connected_devices()
    return render_template('index.html', router_info=router_info, devices=devices)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup a WiFi hotspot and launch the web UI admin panel on the Jetson")
    parser.add_argument("--ssid", type=str, default="RDCJetson", help="SSID for the hotspot")
    parser.add_argument("--password", type=str, default="jetson123", help="Password for the hotspot (min 8 characters)")
    parser.add_argument("--name", type=str, default="RDCJetson", help="Name of the NetworkManager connection")
    parser.add_argument("--skip-network", action="store_true", help="Skip creating the network and just start the Web UI")
    
    args = parser.parse_args()
    
    if not args.skip_network:
        if args.password and len(args.password) < 8:
            print("Error: Password must be at least 8 characters long.")
            sys.exit(1)
        setup_hotspot(args.ssid, args.password, args.name)
        
    print("Starting Web Admin server on port 80...")
    app.run(host='0.0.0.0', port=80)
