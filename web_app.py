import subprocess
import re
from flask import Flask, render_template

app = Flask(__name__)

def get_wifi_interface():
    try:
        output = subprocess.check_output("nmcli -t -f DEVICE,TYPE d", shell=True, text=True)
        for line in output.split('\n'):
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == 'wifi':
                return parts[0]
    except Exception:
        pass
    return None

def get_router_info():
    iface = get_wifi_interface()
    info = {
        'interface': iface,
        'ip': 'Unknown',
        'ssid': 'Unknown',
        'status': 'Inactive'
    }
    if iface:
        try:
            # Check IP
            ip_out = subprocess.check_output(f"ip -4 addr show {iface} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}'", shell=True, text=True)
            if ip_out:
                info['ip'] = ip_out.strip()
            
            # Check current NetworkManager connection
            con_out = subprocess.check_output(f"nmcli -t -f GENERAL.CONNECTION dev show {iface}", shell=True, text=True)
            ssid = con_out.split(':')[1].strip()
            if ssid and ssid != '--':
                info['ssid'] = ssid
                info['status'] = 'Active'
        except Exception:
            pass
    return info

def get_connected_devices():
    iface = get_wifi_interface()
    devices = []
    if iface:
        try:
            # Parse ip neigh (ARP/NDISC neighbor table)
            output = subprocess.check_output(f"ip neigh show dev {iface}", shell=True, text=True)
            for line in output.split('\n'):
                # Ignore failed or incomplete probes
                if not line.strip() or 'FAILED' in line or 'INCOMPLETE' in line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    ip = parts[0]
                    mac = parts[4]
                    state = parts[-1]
                    devices.append({'ip': ip, 'mac': mac, 'state': state})
        except Exception:
            pass
    return devices

@app.route('/')
def index():
    router_info = get_router_info()
    devices = get_connected_devices()
    return render_template('index.html', router_info=router_info, devices=devices)

if __name__ == '__main__':
    # Listen on all interfaces (0.0.0.0) so connected devices can view it
    app.run(host='0.0.0.0', port=80)
