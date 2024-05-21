import sys
import argparse
from tango import Database, DbDevInfo, ConnectionFailed

# This script registers device servers for all paint tanks and mixing tank of multiple stations
parser = argparse.ArgumentParser(
                    prog='register-server.py',
                    description='Register device server with Tango')
parser.add_argument('stations', nargs='+', help='list of paint mixing stations (e.g. station1 station2 station3)')

args = parser.parse_args()

# Reference to the Tango database
try:
    db = Database()
except ConnectionFailed as e:
    print("Error connecting to the Tango database:\n%s" % e)
    sys.exit(0)

# List of devices to register for each station
device_names = ["cyan", "magenta", "yellow", "black", "white", "mixer"]

for station in args.stations:
    for device_name in device_names:
        device_info = DbDevInfo()
        # Define the Tango Class served by this device server
        device_info._class = "PaintTank"
        # Define the instance name for the device server
        device_info.server = "PaintMixingStation/%s" % station
        # Define the device name
        device_info.name = "epfl/%s/%s" % (station, device_name)
        db.add_device(device_info)
        print("Added device: %s\tinstance: %s\tclass: %s" % (device_info.name, device_info.server, device_info._class))
