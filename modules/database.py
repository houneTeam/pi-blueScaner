import sqlite3
from datetime import datetime
from . import utils
import logging

def initialize_database():
    connection = sqlite3.connect("bluetooth_devices.db")
    cursor = connection.cursor()
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
            pass  # Column already exists

    # Remove 'device_info' column if it exists
    try:
        cursor.execute('''ALTER TABLE devices DROP COLUMN device_info''')
    except sqlite3.OperationalError:
        pass  # Column does not exist

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
            # Get current detection_count and last_count_update from the database
            cursor.execute('SELECT detection_count, last_count_update FROM devices WHERE mac = ?', (mac,))
            result = cursor.fetchone()
            if result:
                existing_detection_count, last_count_update_str = result
                detection_count = existing_detection_count

                current_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

                if last_count_update_str:
                    last_count_update = datetime.strptime(last_count_update_str, "%Y-%m-%d %H:%M:%S")
                    time_diff = (current_time - last_count_update).total_seconds()
                else:
                    time_diff = None

                # If more than 30 minutes have passed or program restarted (last_count_update is missing), increment detection_count
                if time_diff is None or time_diff >= 1800:
                    detection_count += 1
                    last_count_update = timestamp
                else:
                    last_count_update = last_count_update_str
            else:
                # If record doesn't exist, set initial values
                detection_count = 1
                last_count_update = timestamp

            # Build UPDATE query dynamically based on provided data
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
            # Update detection_count and last_count_update
            update_fields.append("detection_count = ?")
            params.append(detection_count)
            update_fields.append("last_count_update = ?")
            params.append(last_count_update)
            # Add MAC address to parameters
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
            ''', (device_name, mac, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                  service_data, tx_power, platform_data, gps_data, service_list, detection_count, timestamp))

        connection.commit()
        connection.close()
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
    except Exception as e:
        logging.error(f"Error saving device to database: {e}")
        print(f"Error saving device to database: {e}")

def device_exists(mac):
    try:
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute('''SELECT COUNT(*) FROM devices WHERE mac = ?''', (mac,))
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
        cursor.execute('''SELECT COUNT(*) FROM devices''')
        total_devices = cursor.fetchone()[0]
        cursor.execute('''SELECT COUNT(*) FROM devices WHERE name != "Unknown"''')
        named_devices = cursor.fetchone()[0]
        cursor.execute('''SELECT COUNT(*) FROM devices WHERE service IS NOT NULL AND service != ""''')
        devices_with_service = cursor.fetchone()[0]
        connection.close()
        return total_devices, named_devices, devices_with_service
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
        return 0, 0, 0

def get_detection_count(mac):
    try:
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute("SELECT detection_count FROM devices WHERE mac = ?", (mac,))
        result = cursor.fetchone()
        connection.close()
        if result:
            return result[0]
        else:
            return 0
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
        return 0

def get_device_services(mac):
    try:
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute("SELECT service FROM devices WHERE mac = ?", (mac,))
        result = cursor.fetchone()
        connection.close()
        if result and result[0]:
            return result[0]
        else:
            return None
    except sqlite3.DatabaseError as e:
        logging.error(f"Database error: {e}")
        print(f"Database error: {e}")
        return None
