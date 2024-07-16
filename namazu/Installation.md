Sensor:

1. Run setup script 
chmod +x setup.sh
./setup.sh
2. Upload inventory file
3. Add sensor.py as a service system 
4. sudo usermod -a -G dialout $USER


Sender

1. Install libraries manually
2. Add sender.py as a service system


Receiver
1. Install libraries manually
2. Upload MP3 files
3. Add receiver.py as a service system

screen /dev/ttyACM0 9600
minicom -b 9600 -o -D /dev/ttyACM0

obspy, pygame, pyserial, pyyaml

dmesg | grep tty


make sure serial is enabled: sudo usermod -a -G dialout $USER


sudo apt install -y build-essential gfortran libatlas-base-dev
sudo apt-get install -y libxml2-dev libxslt-dev
sudo apt-get install -y libjpeg-dev libtiff-dev zlib1g-dev
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"
