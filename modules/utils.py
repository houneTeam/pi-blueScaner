# modules/utils.py

import re
import time
import pickle
import os

# Глобальные переменные для хранения GPS-данных и статуса
gps_status = "offline"
latest_gps_coords = {"latitude": None, "longitude": None}
last_gps_update_time = None  # Время последнего обновления GPS

scanning_started = False  # Флаг, указывающий, началось ли сканирование

GPS_DATA_TIMEOUT = 300  # Время в секундах, после которого GPS-данные считаются устаревшими

device_last_count_update = {}  # Словарь для хранения last_count_update для каждого MAC-адреса

def is_mac_address(name):
    mac_pattern = r'([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}'
    return re.fullmatch(mac_pattern, name) is not None

def is_gps_data_fresh():
    """Проверяет, являются ли GPS-данные актуальными."""
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

# Загрузка словаря при запуске
device_last_count_update = load_device_last_count_update()
