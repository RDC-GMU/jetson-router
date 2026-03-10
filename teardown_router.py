#!/usr/bin/env python3
import subprocess
import sys
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

def teardown_hotspot(con_name):
    print(f"Stopping and removing WiFi hotspot '{con_name}'...")
    
    con_output = run_command("nmcli -t -f NAME con show", check=False)
    if con_output:
        for line in con_output.split('\n'):
            if line == con_name:
                print(f"Deactivating connection: {line}")
                run_command(f"nmcli con down '{line}'", check=False)
                
                print(f"Removing connection: {line}")
                run_command(f"nmcli con delete '{line}'", check=False)
                print("Hotspot successfully removed.")
                return
                
    print(f"Hotspot connection '{con_name}' not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teardown the WiFi hotspot on the Jetson")
    parser.add_argument("--name", type=str, default="RDCJetson", help="Name of the NetworkManager connection to remove")
    
    args = parser.parse_args()
    teardown_hotspot(args.name)
