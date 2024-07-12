import os
import paramiko
from obspy.clients.fdsn import Client as FDSNClient

# Configuration for your Raspberry Shake and local machine
RS_SERVER = "http://data.raspberryshake.org"
NETWORK = "AM"
STATION = "R8C49"  # Replace with your station code
USERNAME = "myshake"  # Default username for Raspberry Shake
PASSWORD = "shakeme"  # Default password for Raspberry Shake
SHAKE_IP = "192.168.1.108"  # IP address of your Raspberry Shake
SSH_PORT = 22  # Default SSH port
REMOTE_PATH = "/opt/settings/config/sensor_config.yaml"  # Path to upload the inventory file on the Raspberry Shake
LOCAL_PATH = "namazuc/sensor_config.yaml"  # Path to save the inventory file locally

# Function to upload the inventory file to the Raspberry Shake via SSH
def upload_file():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SHAKE_IP, port=SSH_PORT, username=USERNAME, password=PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_PATH, REMOTE_PATH)
        sftp.close()
        ssh.close()
        print(f"File uploaded to '{REMOTE_PATH}' on Raspberry Shake")
    except Exception as e:
        print(f"Error uploading inventory file: {e}")

if __name__ == "__main__":
    if os.path.exists(LOCAL_PATH):
        upload_file()
    else:
        print(f"File '{LOCAL_PATH}' does not exist.")
