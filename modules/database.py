# modules/database.py

import sqlite3
from datetime import datetime
from . import utils
import logging

def initialize_database():
    connection = sqlite3.connect("bluetooth_devices.db")
    cursor = connection.cursor()

    # 'devices' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mac TEXT UNIQUE,
            rssi INTEGER,
            service TEXT,
            timestamp TEXT,
            adapter TEXT,
            manufacturer_data TEXT,
            service_uuids TEXT,
            service_data TEXT,
            tx_power TEXT,
            platform_data TEXT,
            gps TEXT,
            detection_count INTEGER DEFAULT 1,
            last_count_update TEXT
        )
    ''')
    connection.commit()

    # Add new columns if they don't exist
    columns = ["service", "last_count_update"]
    for column in columns:
        try:
            cursor.execute(f'ALTER TABLE devices ADD COLUMN {column} TEXT')
        except sqlite3.OperationalError:
            pass

    # Remove old column if it exists
    try:
        cursor.execute('''ALTER TABLE devices DROP COLUMN device_info''')
    except sqlite3.OperationalError:
        pass

    # gatt_services table to store expanded GATT data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gatt_services (
            mac TEXT PRIMARY KEY,
            service TEXT
        )
    ''')

    connection.commit()
    connection.close()

def save_device_to_db(device_name, mac, rssi, timestamp, adapter, manufacturer_data,
                      service_uuids, service_data, tx_power, platform_data, gps_data,
                      service_list=None, detection_count=1,
                      update_existing=False):
    try:
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()

        if update_existing:
            cursor.execute('SELECT detection_count, last_count_update FROM devices WHERE mac = ?', (mac,))
            result = cursor.fetchone()
            if result:
                existing_detection_count, last_count_update_str = result
                detection_count = existing_detection_count

                if last_count_update_str:
                    last_count_update_time = datetime.strptime(last_count_update_str, "%Y-%m-%d %H:%M:%S")
                    current_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    time_diff = (current_time - last_count_update_time).total_seconds()
                else:
                    time_diff = None

                if time_diff is None or time_diff >= 1800:
                    detection_count += 1
                    last_count_update_str = timestamp
            else:
                detection_count = 1
                last_count_update_str = timestamp

            update_fields = []
            params = []

            if device_name is not None:
                update_fields.append("name = ?")
                params.append(device_name)
            if rssi is not None:
                update_fields.append("rssi = ?")
                params.append(rssi)
            if timestamp is not None:
                update_fields.append("timestamp = ?")
                params.append(timestamp)
            if adapter is not None:
                update_fields.append("adapter = ?")
                params.append(adapter)
            if manufacturer_data is not None:
                update_fields.append("manufacturer_data = ?")
                params.append(manufacturer_data)
            if service_uuids is not None:
                update_fields.append("service_uuids = ?")
                params.append(service_uuids)
            if service_data is not None:
                update_fields.append("service_data = ?")
                params.append(service_data)
            if tx_power is not None:
                update_fields.append("tx_power = ?")
                params.append(tx_power)
            if platform_data is not None:
                update_fields.append("platform_data = ?")
                params.append(platform_data)
            if gps_data is not None:
                update_fields.append("gps = ?")
                params.append(gps_data)
            if service_list is not None:
                update_fields.append("service = ?")
                params.append(service_list)

            update_fields.append("detection_count = ?")
            params.append(detection_count)
            update_fields.append("last_count_update = ?")
            params.append(last_count_update_str)
            params.append(mac)

            update_query = f'''
                UPDATE devices SET
                    {', '.join(update_fields)}
                WHERE mac = ?
            '''
            cursor.execute(update_query, params)

        else:
            # Insert new record
            cursor.execute('''
                INSERT OR IGNORE INTO devices (
                    name, mac, rssi, timestamp, adapter, manufacturer_data,
                    service_uuids, service_data, tx_power, platform_data, gps,
                    service, detection_count, last_count_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_name,
                mac,
                rssi,
                timestamp,
                adapter,
                manufacturer_data,
                service_uuids,
                service_data,
                tx_power,
                platform_data,
                gps_data,
                service_list,
                detection_count,
                timestamp
            ))

        connection.commit()
        connection.close()

    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
    except Exception as e:
        logging.error(f"Error saving device to database: {e}")
        print(f"Error saving device to database: {e}")

def update_gatt_services(mac, services):
    """Insert or update GATT services info into the 'gatt_services' table."""
    try:
        conn = sqlite3.connect("bluetooth_devices.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO gatt_services (mac, service)
            VALUES (?, ?)
            ON CONFLICT(mac) DO UPDATE SET service = excluded.service
        """, (mac, services))
        conn.commit()
        conn.close()
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error (gatt_services): {e}")
        print(f"Database error (gatt_services): {e}")
    except Exception as e:
        logging.error(f"Error updating gatt_services: {e}")
        print(f"Error updating gatt_services: {e}")

def device_exists(mac):
    try:
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM devices WHERE mac = ?', (mac,))
        result = cursor.fetchone()[0]
        connection.close()
        return result > 0
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
        return False

def get_database_statistics():
    try:
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM devices')
        total_devices = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM devices WHERE name != "Unknown"')
        named_devices = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM devices WHERE service IS NOT NULL AND service != ""')
        devices_with_service = cursor.fetchone()[0]
        connection.close()
        return total_devices, named_devices, devices_with_service
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
        return 0, 0, 0

