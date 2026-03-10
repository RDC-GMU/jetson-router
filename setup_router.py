#!/usr/bin/env python3
import subprocess
import sys
import time
import argparse

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
    output = run_command("nmcli -t -f DEVICE,TYPE d")
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup a WiFi hotspot (internal network) on the Jetson")
    parser.add_argument("--ssid", type=str, default="RDCJetson", help="SSID for the hotspot")
    parser.add_argument("--password", type=str, default="jetson123", help="Password for the hotspot (min 8 characters)")
    parser.add_argument("--name", type=str, default="RDCJetson", help="Name of the NetworkManager connection")
    
    args = parser.parse_args()
    
    if args.password and len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)
        
    setup_hotspot(args.ssid, args.password, args.name)
