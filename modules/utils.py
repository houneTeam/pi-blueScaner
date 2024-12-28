# modules/utils.py

import re
import time
import pickle
import os

gps_status = "offline"
latest_gps_coords = {"latitude": None, "longitude": None}
last_gps_update_time = None  # Time of last GPS update

scanning_started = False
device_being_processed = False

GPS_DATA_TIMEOUT = 300

device_last_count_update = {}

connect_mode = True  # We can just set this to True by default if you like
gps_data_received = False
use_gps = False

max_connect = 5  # Default concurrency limit

def is_mac_address(name):
    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    return re.fullmatch(mac_pattern, name) is not None

def is_gps_data_fresh():
    if not use_gps:
        return False
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

device_last_count_update = load_device_last_count_update()
