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
import sqlite3
from .database import save_device_to_db, device_exists, get_database_statistics
from .utils import is_mac_address
from . import utils  # Для доступа к глобальным переменным

def get_bluetooth_interfaces():
    try:
        result = subprocess.run(["hciconfig"], capture_output=True, text=True, check=True)
        interfaces = []
        for line in result.stdout.splitlines():
            if line.startswith("hci"):  # Detect interface lines
                parts = line.split()
                interface = parts[0].strip(":")
                bus_info = "USB" if "Bus: USB" in line else "UART" if "Bus: UART" in line else "Unknown"
                interfaces.append((interface, bus_info))
        return interfaces
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get Bluetooth interfaces: {e}")
        return []

async def scan_ble_devices(adapter, update_mode):
    last_info_time = time.time()
    last_gps_status = utils.gps_status  # Track the last displayed GPS status to avoid spam

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
        rssi_display = colored(f"{rssi}", "magenta", attrs=["bold"])  # Display RSSI in bright purple

        # Проверяем, существует ли устройство в базе данных и получаем текущий RSSI и GPS данные
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute("SELECT rssi FROM devices WHERE mac = ?", (device.address,))
        existing_data = cursor.fetchone()
        connection.close()

        # Преобразуем RSSI в целые числа для сравнения
        try:
            rssi = int(rssi)
        except ValueError:
            rssi = None

        if existing_data:
            existing_rssi = existing_data[0]
            try:
                existing_rssi = int(existing_rssi)
            except ValueError:
                existing_rssi = None

            # Проверяем, улучшился ли сигнал (RSSI стал ближе к нулю)
            if rssi is not None and existing_rssi is not None and rssi > existing_rssi:
                # Обновляем RSSI и GPS в базе данных
                if update_mode:
                    print(f"{colored('[RSSI IMPROVED]', 'cyan')} {device_name} (Interface: {adapter}) {rssi_display}")
                    # Используем последние известные GPS координаты
                    if utils.latest_gps_coords["latitude"] and utils.latest_gps_coords["longitude"]:
                        gps_data = f"{utils.latest_gps_coords['latitude']}, {utils.latest_gps_coords['longitude']}"
                    else:
                        gps_data = "No GPS data"
                    save_device_to_db(
                        device_name, device.address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                        service_data, tx_power, platform_data, gps_data, update_existing=True
                    )
                    print(f"{colored('[UPDATED]', 'yellow')} {device_name} RSSI and GPS updated.")
                else:
                    print(f"{colored('[exists]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
            else:
                print(f"{colored('[exists]', 'yellow')} {device_name} (Interface: {adapter}) {rssi_display}")
        else:
            # Устройство новое, сохраняем его
            print(f"{colored('[NEW]', 'green')} {device_name} (Interface: {adapter}) {rssi_display}")
            # Используем последние известные GPS координаты
            if utils.latest_gps_coords["latitude"] and utils.latest_gps_coords["longitude"]:
                gps_data = f"{utils.latest_gps_coords['latitude']}, {utils.latest_gps_coords['longitude']}"
            else:
                gps_data = "No GPS data"
            save_device_to_db(
                device_name, device.address, rssi, timestamp, adapter, manufacturer_data, service_uuids,
                service_data, tx_power, platform_data, gps_data
            )

        # После сохранения или обновления устройства, получаем detection_count
        connection = sqlite3.connect("bluetooth_devices.db")
        cursor = connection.cursor()
        cursor.execute("SELECT detection_count FROM devices WHERE mac = ?", (device.address,))
        detection_count = cursor.fetchone()[0]
        connection.close()

        print(f"{colored('[INFO]', 'blue')} Device {device_name} detected {detection_count} times.")

        # Выводим статистику каждые 5 секунд
        if time.time() - last_info_time >= 5:
            last_info_time = time.time()
            total_devices, named_devices = get_database_statistics()
            print(f"{colored('[INFO]', 'blue')} Total devices in database: {total_devices}, Named devices: {named_devices}")

    scanner = BleakScanner(adapter=adapter, detection_callback=detection_callback)
    logging.info("Starting Bluetooth scanning...")
    await scanner.start()
    try:
        while True:
            # Проверяем статус GPS каждую секунду, выводим только если статус изменился
            if utils.gps_status != last_gps_status:
                last_gps_status = utils.gps_status
                print(f"{colored('[GPS STATUS]', 'cyan' if utils.gps_status == 'online' else 'red')} GPS is {utils.gps_status}.")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logging.info("Stopping Bluetooth scanning...")
    finally:
        await scanner.stop()
