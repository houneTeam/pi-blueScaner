# modules/bluetooth_scanner.py

import asyncio
import subprocess
import logging
import time
from datetime import datetime
from termcolor import colored
from bleak import BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .database import (
    save_device_to_db,
    device_exists,
    get_database_statistics,
)
from .utils import is_mac_address
from . import utils
from .device_connector import connect_to_device

def get_bluetooth_interfaces():
    """Return a list of available Bluetooth interfaces (hciN) with bus info."""
    try:
        result = subprocess.run(["hciconfig"], capture_output=True, text=True, check=True)
        interfaces = []
        current_interface = None
        bus_info = "Unknown"
        for line in result.stdout.splitlines():
            if line.startswith("hci"):
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

async def start_continuous_scan_and_connect(adapter):
    """
    Continuously scan for BLE devices using the single 'adapter',
    then attempt to connect to each discovered device (limited by a semaphore).
    """
    # Create a semaphore based on user’s chosen concurrency limit
    semaphore = asyncio.Semaphore(utils.max_connect)

    # For logging and stats
    detection_counts = {}
    last_info_time = time.time()

    while True:
        print(f"{colored('[INFO]', 'blue')} Scanning on {adapter}...")
        logging.info(f"Scanning for devices on {adapter}...")
        
        try:
            scanner = BleakScanner(adapter=adapter)
            devices = await scanner.discover(timeout=3.0)
        except BleakError as e:
            logging.error(f"Failed to scan on adapter {adapter}: {e}")
            print(f"{colored('[ERROR]', 'red')} Failed to scan on {adapter}. Is the adapter powered on?")
            await asyncio.sleep(3)
            continue

        if not devices:
            print("No devices found.")
            logging.info("No devices found.")
            await asyncio.sleep(3)
            continue

        # For each discovered device, update or insert into 'devices' table and connect
        tasks = []
        for device in devices:
            mac_address = device.address
            device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            rssi = device.rssi if device.rssi is not None else -100
            rssi_display = colored(f"{rssi}", "magenta", attrs=["bold"])

            # GPS data if available
            if utils.use_gps and utils.is_gps_data_fresh():
                gps_data = f"{utils.latest_gps_coords['latitude']}, {utils.latest_gps_coords['longitude']}"
            else:
                gps_data = None

            # Save device (name, mac, etc.) to the main 'devices' table
            if device_exists(mac_address):
                print(f"{colored('[UPDATED]', 'yellow')} {device_name} (Interface: {adapter}) RSSI: {rssi_display}")
                save_device_to_db(
                    device_name,
                    mac_address,
                    rssi,
                    timestamp,
                    adapter,
                    manufacturer_data=None,
                    service_uuids=None,
                    service_data=None,
                    tx_power=None,
                    platform_data=None,
                    gps_data=gps_data,
                    service_list=None,
                    update_existing=True
                )
            else:
                print(f"{colored('[NEW]', 'green')} {device_name} (Interface: {adapter}) RSSI: {rssi_display}")
                save_device_to_db(
                    device_name,
                    mac_address,
                    rssi,
                    timestamp,
                    adapter,
                    manufacturer_data=None,
                    service_uuids=None,
                    service_data=None,
                    tx_power=None,
                    platform_data=None,
                    gps_data=gps_data,
                    service_list=None
                )

            # For stats
            detection_counts[mac_address] = detection_counts.get(mac_address, 0) + 1
            detection_count = detection_counts[mac_address]
            print(f"{colored('[INFO]', 'blue')} Device {device_name} seen {detection_count} times.")

            # Always connect in this “scan+connect” mode
            tasks.append(connect_to_device(device, adapter, semaphore))

        # Show DB stats every ~5 seconds
        if time.time() - last_info_time >= 5:
            last_info_time = time.time()
            total_devices, named_devices, devices_with_service = get_database_statistics()
            print(
                f"{colored('[INFO]', 'blue')} Total: {total_devices} | "
                f"Named: {named_devices} | With Service Info: {colored(devices_with_service, 'yellow')}"
            )

        # Connect to all discovered devices with concurrency control
        if tasks:
            await asyncio.gather(*tasks)

        print("\n[INFO] Waiting before next scan...\n")
        logging.info("Restarting scan...")
        await asyncio.sleep(3)
