import asyncio
import subprocess
import logging
import time
from datetime import datetime
from termcolor import colored
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from .database import (
    save_device_to_db,
    device_exists,
    get_database_statistics,
    get_detection_count,
    get_device_services,
)
from .utils import is_mac_address
from . import utils
from .device_connector import devices_to_connect
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

    detection_counts = {}
    rssi_threshold = -70  # Adjust as needed
    detection_threshold = 3  # Adjust as needed

    def device_has_services(mac):
        services = get_device_services(mac)
        return services is not None

    def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        nonlocal last_info_time

        rssi = device.rssi if device.rssi is not None else -100
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

        mac_address = device.address

        # Increment detection count
        detection_counts[mac_address] = detection_counts.get(mac_address, 0) + 1
        detection_count = detection_counts[mac_address]

        # Save device to database
        if device_exists(mac_address):
            if update_mode:
                print(f"{colored('[UPDATED]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
                save_device_to_db(
                    device_name, mac_address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                    service_data, tx_power, platform_data, gps_data=gps_data,
                    service_list=None,
                    update_existing=True
                )
            else:
                print(f"{colored('[exists]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
        else:
            print(f"{colored('[NEW]', 'green')} {device_name} (Interface: {adapter}) {rssi_display}")
            save_device_to_db(
                device_name, mac_address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                service_data, tx_power, platform_data, gps_data=gps_data,
                service_list=None
            )

        print(f"{colored('[INFO]', 'blue')} Device {device_name} detected {detection_count} times.")

        # Check if device meets criteria to connect
        if (detection_count >= detection_threshold and rssi >= rssi_threshold and
                not device_has_services(mac_address)):
            if not utils.device_being_processed:
                devices_to_connect.put_nowait(device)
                print(f"{colored('[QUEUE]', 'yellow')} Added {device_name} ({mac_address}) to connection queue.")

        if time.time() - last_info_time >= 5:
            last_info_time = time.time()
            total_devices, named_devices, devices_with_service = get_database_statistics()
            devices_with_service_display = colored(f"{devices_with_service}", "yellow")
            print(
                f"{colored('[INFO]', 'blue')} Total devices in database: {total_devices}, "
                f"Named devices: {named_devices}, Devices with service info: {devices_with_service_display}"
            )

    scanner = BleakScanner(adapter=adapter)
    scanner.register_detection_callback(detection_callback)
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

