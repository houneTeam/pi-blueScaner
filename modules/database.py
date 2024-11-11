# modules/database.py

import sqlite3
from datetime import datetime
from . import utils

def initialize_database():
    connection = sqlite3.connect("bluetooth_devices.db")
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mac TEXT UNIQUE,
            rssi INTEGER,
            timestamp TEXT,
            adapter TEXT,
            manufacturer_data TEXT,
            service_uuids TEXT,
            service_data TEXT,
            tx_power TEXT,
            platform_data TEXT,
            gps TEXT,
            detection_count INTEGER DEFAULT 1
        )
    ''')
    connection.commit()

    # Добавляем новую колонку detection_count, если она отсутствует
    try:
        cursor.execute('ALTER TABLE devices ADD COLUMN detection_count INTEGER DEFAULT 1')
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

    connection.commit()
    connection.close()

def save_device_to_db(device_name, mac, rssi, timestamp, adapter, manufacturer_data,
                      service_uuids, service_data, tx_power, platform_data, gps_data,
                      update_existing=False):
    connection = sqlite3.connect("bluetooth_devices.db")
    cursor = connection.cursor()

    if update_existing:
        # Получаем текущий detection_count из базы данных
        cursor.execute('SELECT detection_count FROM devices WHERE mac = ?', (mac,))
        result = cursor.fetchone()
        if result:
            detection_count = result[0]
            current_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            
            # Получаем last_count_update из словаря
            last_count_update_str = utils.device_last_count_update.get(mac)
            if last_count_update_str:
                last_count_update = datetime.strptime(last_count_update_str, "%Y-%m-%d %H:%M:%S")
                time_diff = (current_time - last_count_update).total_seconds()
            else:
                time_diff = None

            if time_diff is None or time_diff >= 600:
                # Увеличиваем detection_count и обновляем last_count_update в словаре
                detection_count += 1
                utils.device_last_count_update[mac] = timestamp
            # Если прошло меньше 10 минут, detection_count не изменяется

            # Обновляем запись в базе данных
            cursor.execute('''
                UPDATE devices SET
                    name = ?,
                    rssi = ?,
                    timestamp = ?,
                    adapter = ?,
                    manufacturer_data = ?,
                    service_uuids = ?,
                    service_data = ?,
                    tx_power = ?,
                    platform_data = ?,
                    gps = ?,
                    detection_count = ?
                WHERE mac = ?
            ''', (device_name, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                  service_data, tx_power, platform_data, gps_data, detection_count, mac))
        else:
            # Если записи нет, вставляем новую
            cursor.execute('''
                INSERT INTO devices (name, mac, rssi, timestamp, adapter, manufacturer_data,
                                     service_uuids, service_data, tx_power, platform_data, gps,
                                     detection_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (device_name, mac, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                  service_data, tx_power, platform_data, gps_data, 1))
            # Обновляем last_count_update в словаре
            utils.device_last_count_update[mac] = timestamp
    else:
        # Вставляем новую запись
        cursor.execute('''
            INSERT OR IGNORE INTO devices (name, mac, rssi, timestamp, adapter, manufacturer_data,
                                           service_uuids, service_data, tx_power, platform_data, gps,
                                           detection_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (device_name, mac, rssi, timestamp, adapter, manufacturer_data, service_uuids,
              service_data, tx_power, platform_data, gps_data, 1))
        # Обновляем last_count_update в словаре
        utils.device_last_count_update[mac] = timestamp

    connection.commit()
    connection.close()

def device_exists(mac):
    connection = sqlite3.connect("bluetooth_devices.db")
    cursor = connection.cursor()
    cursor.execute('''SELECT COUNT(*) FROM devices WHERE mac = ?''', (mac,))
    result = cursor.fetchone()[0]
    connection.close()
    return result > 0

def get_database_statistics():
    connection = sqlite3.connect("bluetooth_devices.db")
    cursor = connection.cursor()
    cursor.execute('''SELECT COUNT(*) FROM devices''')
    total_devices = cursor.fetchone()[0]
    cursor.execute('''SELECT COUNT(*) FROM devices WHERE name != "Unknown"''')
    named_devices = cursor.fetchone()[0]
    connection.close()
    return total_devices, named_devices
