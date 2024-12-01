# modules/bluetooth_scanner.py

import asyncio
import subprocess
import logging
import time
from datetime import datetime
from termcolor import colored
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from .database import save_device_to_db, device_exists, get_database_statistics, get_detection_count, get_device_services
from .utils import is_mac_address
from . import utils
from .device_connector import devices_to_connect, devices_to_connect_helper
import sqlite3

def get_bluetooth_interfaces():
    try:
        result = subprocess.run(["hciconfig"], capture_output=True, text=True, check=True)
        interfaces = []
        current_interface = None
        bus_info = "Unknown"
        for line in result.stdout.splitlines():
            if line.startswith("hci"):  # Line with interface
                parts = line.split(":")
                interface = parts[0].strip()
                current_interface = interface
            elif "\t" in line and current_interface:
                if "Bus: USB" in line:
                    bus_info = "USB"
                elif "Bus: UART" in line:
                    bus_info = "UART"
                interfaces.append((current_interface, bus_info))
                current_interface = None
                bus_info = "Unknown"
        return interfaces
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get Bluetooth interfaces: {e}")
        return []

async def scan_ble_devices(adapter, update_mode, helper_mode=False):
    last_info_time = time.time()
    last_gps_status = utils.gps_status

    def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        nonlocal last_info_time

        rssi = advertisement_data.rssi if advertisement_data.rssi is not None else "Unknown"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx_power = advertisement_data.tx_power or "Unknown"
        manufacturer_data = str(advertisement_data.manufacturer_data)
        service_uuids = str(advertisement_data.service_uuids)
        service_data = str(advertisement_data.service_data)
        platform_data = str(advertisement_data.platform_data)

        device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"
        rssi_display = colored(f"{rssi}", "magenta", attrs=["bold"])

        # Get the latest GPS data if it's fresh
        if utils.is_gps_data_fresh():
            gps_data = f"{utils.latest_gps_coords['latitude']}, {utils.latest_gps_coords['longitude']}"
        else:
            gps_data = None

        if device_exists(device.address):
            if update_mode:
                print(f"{colored('[UPDATED]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
                save_device_to_db(
                    device_name, device.address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                    service_data, tx_power, platform_data, gps_data=gps_data,
                    device_info=None, service_list=None,
                    update_existing=True
                )
            else:
                print(f"{colored('[exists]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
        else:
            print(f"{colored('[NEW]', 'green')} {device_name} (Interface: {adapter}) {rssi_display}")
            save_device_to_db(
                device_name, device.address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                service_data, tx_power, platform_data, gps_data=gps_data,
                device_info=None, service_list=None
            )

        detection_count = get_detection_count(device.address)
        print(f"{colored('[INFO]', 'blue')} Device {device_name} detected {detection_count} times.")

        # Add device to queue only if no device is being processed
        if not utils.device_being_processed and utils.connect_mode:
            utils.device_being_processed = True  # Set the flag
            devices_to_connect.put_nowait(device)

        # Similarly for helper mode
        if helper_mode and not utils.device_being_processed and get_device_services(device.address):
            utils.device_being_processed = True  # Set the flag
            devices_to_connect_helper.put_nowait(device)

        if time.time() - last_info_time >= 5:
            last_info_time = time.time()
            total_devices, named_devices = get_database_statistics()
            print(f"{colored('[INFO]', 'blue')} Total devices in database: {total_devices}, Named devices: {named_devices}")

    scanner = BleakScanner(adapter=adapter, detection_callback=detection_callback)
    logging.info("Starting Bluetooth scanning...")
    print(f"{colored('[INFO]', 'blue')} Starting Bluetooth scanning on adapter {adapter}...")
    await scanner.start()
    utils.scanning_started = True  # Set flag after starting scanning
    try:
        while True:
            if utils.gps_status != last_gps_status:
                last_gps_status = utils.gps_status
                status_color = 'cyan' if utils.gps_status == 'online' else 'red'
                print(f"{colored('[GPS STATUS]', status_color)} GPS is {utils.gps_status}.")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logging.info("Stopping Bluetooth scanning...")
    finally:
        await scanner.stop()
        utils.scanning_started = False  # Reset flag after stopping scanning
        print(f"{colored('[INFO]', 'blue')} Stopped Bluetooth scanning on adapter {adapter}.")

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
