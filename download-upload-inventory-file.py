import os
import paramiko
from obspy.clients.fdsn import Client as FDSNClient

# Configuration for your Raspberry Shake and local machine
RS_SERVER = "http://data.raspberryshake.org"
NETWORK = "AM"
STATION = "RA9CD"  # Replace with your station code
USERNAME = "myshake"  # Default username for Raspberry Shake
PASSWORD = "shakeme"  # Default password for Raspberry Shake
SHAKE_IP = "192.168.1.185"  # IP address of your Raspberry Shake
SSH_PORT = 22  # Default SSH port
REMOTE_PATH = "/opt/settings/config/inventory.xml"  # Path to upload the inventory file on the Raspberry Shake
LOCAL_PATH = "inventory.xml"  # Path to save the inventory file locally

# Function to download the inventory file from the Raspberry Shake server
def download_inventory():
    try:
        client = FDSNClient(RS_SERVER)
        inventory = client.get_stations(network=NETWORK, station=STATION, level="response")
        inventory.write(LOCAL_PATH, format="STATIONXML")
        print(f"Inventory file downloaded and saved as '{LOCAL_PATH}'")
    except Exception as e:
        print(f"Error downloading inventory file: {e}")

# Function to upload the inventory file to the Raspberry Shake via SSH
def upload_inventory():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SHAKE_IP, port=SSH_PORT, username=USERNAME, password=PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_PATH, REMOTE_PATH)
        sftp.close()
        ssh.close()
        print(f"Inventory file uploaded to '{REMOTE_PATH}' on Raspberry Shake")
    except Exception as e:
        print(f"Error uploading inventory file: {e}")

if __name__ == "__main__":
    # Download the inventory file from the Raspberry Shake server
    download_inventory()
    
    # Upload the inventory file to the Raspberry Shake
    if os.path.exists(LOCAL_PATH):
        upload_inventory()
    else:
        print(f"Inventory file '{LOCAL_PATH}' does not exist.")
