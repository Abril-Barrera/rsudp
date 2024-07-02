#!/bin/bash

# Update package list and install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev libatlas-base-dev libfreetype6-dev libjpeg-dev libpng-dev

# Install Python libraries from requirements.txt
pip3 install -r requirements.txt
