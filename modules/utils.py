# modules/utils.py

import re
import time
import pickle
import os

# Global variables for GPS data and status
gps_status = "offline"
latest_gps_coords = {"latitude": None, "longitude": None}
last_gps_update_time = None  # Time of last GPS update

scanning_started = False  # Flag indicating whether scanning has started
device_being_processed = False  # Flag indicating that a device is being processed

GPS_DATA_TIMEOUT = 300  # Time in seconds after which GPS data is considered stale

device_last_count_update = {}  # Dictionary to store last_count_update for each MAC address

connect_mode = False       # Flag indicating the connect mode
gps_data_received = False  # Flag indicating whether GPS data has been received

def is_mac_address(name):
    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    return re.fullmatch(mac_pattern, name) is not None

def is_gps_data_fresh():
    """Checks if GPS data is fresh."""
    if last_gps_update_time is None:
        return False
    return (time.time() - last_gps_update_time) <= GPS_DATA_TIMEOUT

def load_device_last_count_update():
    if os.path.exists("device_last_count_update.pkl"):
        with open("device_last_count_update.pkl", "rb") as f:
            return pickle.load(f)
    return {}

def save_device_last_count_update():
    with open("device_last_count_update.pkl", "wb") as f:
        pickle.dump(device_last_count_update, f)

# Load the dictionary on startup
device_last_count_update = load_device_last_count_update()
