#!/usr/bin/env python3
import subprocess
import sys
import time
import argparse
import re
import os
import json
from flask import Flask, render_template, request, redirect

def run_command(command, check=True):
    try:
        result = subprocess.run(command, check=check, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr.strip() if e.stderr else ''}")
        if check:
            sys.exit(1)
        return ""

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

app = Flask(__name__)

def get_router_info():
    iface = get_wifi_interface()
    info = {
        'interface': iface,
        'ip': 'Unknown',
        'ssid': 'Unknown',
        'password': 'Unknown',
        'status': 'Inactive',
        'frequency': 'Unknown',
        'total_channels': 'Unknown',
        'current_channel': 'Unknown',
        'available_channels': []
    }
    if iface:
        try:
            ip_out = run_command(f"ip -4 addr show {iface} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}'", check=False)
            if ip_out:
                info['ip'] = ip_out.strip()
            
            con_out = run_command(f"nmcli -t -f GENERAL.CONNECTION dev show {iface}", check=False)
            if not con_out:
                return info
            con_parts = con_out.split(':')
            if len(con_parts) > 1:
                con_name = con_parts[1].strip()
            else:
                return info
            if con_name and con_name != '--':
                info['ssid'] = con_name
                info['status'] = 'Active'
                try:
                    actual_ssid = run_command(f"nmcli -t -f 802-11-wireless.ssid connection show '{con_name}'", check=False)
                    if actual_ssid and ':' in actual_ssid:
                        info['ssid'] = actual_ssid.split(':', 1)[1].strip()
                except Exception:
                    pass
                try:
                    psk = run_command(f"nmcli -s -g 802-11-wireless-security.psk connection show '{con_name}'", check=False)
                    if psk:
                        info['password'] = psk
                    else:
                        info['password'] = 'None (Open Network)'
                except Exception:
                    info['password'] = 'Unknown'

                try:
                    available_channels = []
                    current_channel = ""
                    freq_out = run_command(f"iwlist {iface} freq", check=False)
                    if freq_out:
                        for line in freq_out.split('\n'):
                            line = line.strip()
                            if line.startswith("Channel "):
                                match = re.search(r'Channel\s+(\d+)\s+:', line)
                                if match:
                                    available_channels.append(str(int(match.group(1))))
                            elif "Current Frequency:" in line:
                                info['frequency'] = line.split('Current Frequency:')[1].strip()
                                match = re.search(r'Channel\s+(\d+)', info['frequency'])
                                if match:
                                    current_channel = str(int(match.group(1)))
                            elif "channels in total" in line:
                                match = re.search(r'(\d+) channels in total', line)
                                if match:
                                    info['total_channels'] = match.group(1)
                    
                    if not current_channel:
                        try:
                            chan_out = run_command(f"nmcli -t -f 802-11-wireless.channel connection show '{con_name}'", check=False)
                            if chan_out and ':' in chan_out:
                                conf_chan = chan_out.split(':', 1)[1].strip()
                                if conf_chan == '0':
                                    info['frequency'] = 'Auto (Selected by OS)'
                                    current_channel = '0'
                                elif conf_chan:
                                    current_channel = conf_chan
                                    info['frequency'] = f"Channel {conf_chan}"
                        except Exception:
                            pass
                    
                    info['available_channels'] = available_channels
                    info['current_channel'] = current_channel
                except Exception:
                    info['frequency'] = 'Unavailable'
                    info['total_channels'] = 'Unavailable'
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
            output = run_command(f"ip neigh show dev {iface}", check=False)
            if output:
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

PORT_FORWARD_CONF = "/etc/NetworkManager/jetson_port_forwards.json"

def apply_port_forwards():
    try:
        pass
        forwards = get_port_forwards()
        
        router_ip = ''
        iface = get_wifi_interface()
        if iface:
            try:
                ip_out = subprocess.check_output(f"ip -4 addr show {iface} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}'", shell=True, text=True)
                if ip_out:
                    router_ip = ip_out.strip()
            except Exception:
                pass
        
        subprocess.run("iptables -t nat -F PREROUTING", shell=True)
        
        for fw in forwards:
            src_port = fw.get('src_port')
            dest_ip = fw.get('dest_ip')
            dest_port = fw.get('dest_port')
            if src_port and dest_ip and dest_port:
                if router_ip:
                    cmd = f"iptables -t nat -A PREROUTING -p tcp --dport {src_port} -d {router_ip} -j DNAT --to-destination {dest_ip}:{dest_port}"
                    subprocess.run(cmd, shell=True)
                
    except Exception as e:
        print(f"Error applying port forwards: {e}")

def get_port_forwards():
    forwards = []
    try:
        if os.path.exists(PORT_FORWARD_CONF):
            with open(PORT_FORWARD_CONF, 'r') as f:
                forwards = json.load(f)
    except Exception:
        pass
    return forwards

def set_port_forward(src_port, dest_ip, dest_port, remove=False):
    forwards = get_port_forwards()
    
    forwards = [fw for fw in forwards if str(fw.get('src_port')) != str(src_port)]
    
    if not remove:
        forwards.append({
            'src_port': src_port,
            'dest_ip': dest_ip,
            'dest_port': dest_port
        })
        
    try:
        with open(PORT_FORWARD_CONF, 'w') as f:
            json.dump(forwards, f)
        apply_port_forwards()
        return True
    except Exception as e:
        print(f"Error writing port forward conf: {e}")
        return False

@app.route('/')
def index():
    router_info = get_router_info()
    devices = get_connected_devices()
    port_forwards = get_port_forwards()
    
    return render_template('index.html', router_info=router_info, devices=devices, port_forwards=port_forwards)

@app.route('/set_port_forward', methods=['POST'])
def handle_set_port_forward():
    src_port = request.form.get('src_port')
    dest_ip = request.form.get('dest_ip')
    dest_port = request.form.get('dest_port')
    remove = request.form.get('remove') == 'true'
    
    if src_port:
        set_port_forward(src_port, dest_ip, dest_port, remove)
    return redirect('/')

@app.route('/change_channel', methods=['POST'])
def change_channel():
    iface = get_wifi_interface()
    new_channel = request.form.get('channel')
    
    if iface and new_channel:
        try:
            con_out = run_command(f"nmcli -t -f GENERAL.CONNECTION dev show {iface}", check=False)
            if con_out:
                con_parts = con_out.split(':')
                if len(con_parts) > 1:
                    con_name = con_parts[1].strip()
                    if con_name and con_name != '--':
                        band = 'bg' if int(new_channel) <= 14 else 'a'
                        subprocess.run(f"nmcli con modify '{con_name}' 802-11-wireless.band '{band}'", shell=True)
                        subprocess.run(f"nmcli con modify '{con_name}' 802-11-wireless.channel '{new_channel}'", shell=True)
                        subprocess.run(f"nmcli con up '{con_name}'", shell=True)
        except Exception:
            pass
            
    time.sleep(3)
    return redirect('/')


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
