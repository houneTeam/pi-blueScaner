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
    get_device_services,
)
from .utils import is_mac_address
from . import utils
from .device_connector import connect_to_device
import sqlite3

def get_bluetooth_interfaces():
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

async def scan_ble_devices(adapter, update_mode, helper_mode=False, connect_adapter=False):
    last_info_time = time.time()
    last_gps_status = utils.gps_status

    detection_counts = {}
    rssi_threshold = -70
    detection_threshold = 3

    current_connections = 0

    def device_has_services(mac):
        services = get_device_services(mac)
        return services is not None

    async def handle_device_connection(device):
        nonlocal current_connections
        if current_connections < utils.max_connect:
            current_connections += 1
            await connect_to_device(device, adapter)
            current_connections -= 1
        else:
            print(f"{colored('[INFO]', 'blue')} Max connection limit reached. Skipping {device.address}.")

    def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        nonlocal last_info_time
        rssi = advertisement_data.rssi if advertisement_data.rssi is not None else -100
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx_power = advertisement_data.tx_power or "Unknown"
        manufacturer_data = str(advertisement_data.manufacturer_data)
        service_uuids = str(advertisement_data.service_uuids)
        service_data = str(advertisement_data.service_data)
        platform_data = str(advertisement_data.platform_data)

        device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"
        rssi_display = colored(f"{rssi}", "magenta", attrs=["bold"])

        if utils.use_gps and utils.is_gps_data_fresh():
            gps_data = f"{utils.latest_gps_coords['latitude']}, {utils.latest_gps_coords['longitude']}"
        else:
            gps_data = None

        mac_address = device.address
        detection_counts[mac_address] = detection_counts.get(mac_address, 0) + 1
        detection_count = detection_counts[mac_address]

        # Сохранение в БД
        if device_exists(mac_address):
            if update_mode:
                print(f"{colored('[UPDATED]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
                save_device_to_db(
                    device_name, mac_address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                    service_data, tx_power, platform_data, gps_data=gps_data if utils.use_gps else None,
                    service_list=None,
                    update_existing=True
                )
            else:
                print(f"{colored('[exists]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
        else:
            print(f"{colored('[NEW]', 'green')} {device_name} (Interface: {adapter}) {rssi_display}")
            save_device_to_db(
                device_name, mac_address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                service_data, tx_power, platform_data, gps_data=gps_data if utils.use_gps else None,
                service_list=None
            )

        print(f"{colored('[INFO]', 'blue')} Device {device_name} detected {detection_count} times.")

        if connect_adapter and utils.connect_mode:
            if (detection_count >= detection_threshold and rssi >= rssi_threshold and not device_has_services(mac_address)):
                asyncio.get_event_loop().create_task(handle_device_connection(device))

        if time.time() - last_info_time >= 5:
            last_info_time = time.time()
            total_devices, named_devices, devices_with_service = get_database_statistics()
            devices_with_service_display = colored(f"{devices_with_service}", "yellow")
            print(
                f"{colored('[INFO]', 'blue')} Total devices in database: {total_devices}, "
                f"Named devices: {named_devices}, Devices with service info: {devices_with_service_display}"
            )

    scanner = BleakScanner(adapter=adapter, detection_callback=detection_callback)
    logging.info(f"Starting Bluetooth scanning on adapter {adapter}...")
    print(f"{colored('[INFO]', 'blue')} Starting Bluetooth scanning on adapter {adapter}...")

    try:
        await scanner.start()
    except BleakError as e:
        logging.error(f"Failed to start scanning on adapter {adapter}: {e}")
        print(colored('[ERROR]', 'red'), f"Failed to start scanning on adapter {adapter}. Is the adapter powered on and ready?")
        return

    utils.scanning_started = True
    try:
        while True:
            if utils.use_gps and utils.gps_status != last_gps_status:
                last_gps_status = utils.gps_status
                status_color = 'cyan' if utils.gps_status == 'online' else 'red'
                print(f"{colored('[GPS STATUS]', status_color)} GPS is {utils.gps_status}.")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logging.info("Stopping Bluetooth scanning...")
    finally:
        await scanner.stop()
        utils.scanning_started = False
        print(f"{colored('[INFO]', 'blue')} Stopped Bluetooth scanning on adapter {adapter}.")
