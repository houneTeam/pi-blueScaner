# main.py

import threading
import logging
import asyncio
import atexit
from modules.database import initialize_database
from modules.gps_server import start_gps_server, gps_data_received_event
from modules.bluetooth_scanner import get_bluetooth_interfaces, scan_ble_devices
from termcolor import colored
from modules import utils

def main():
    initialize_database()
    threading.Thread(target=start_gps_server, daemon=True).start()

    # Ожидаем получения GPS-данных
    print("Waiting for GPS data...")
    gps_data_received_event.wait()
    print(f"{colored('[INFO]', 'blue')} GPS data received.")

    # Теперь предлагаем выбрать адаптер и режим сканирования
    interfaces = get_bluetooth_interfaces()
    if not interfaces:
        logging.error("No Bluetooth interfaces found.")
        print("No Bluetooth interfaces found.")
        return

    print("Available Bluetooth interfaces:")
    for idx, (interface, bus_info) in enumerate(interfaces):
        print(f"{idx}: {interface} ({colored(bus_info, 'magenta')})")

    try:
        selected_index = input("Select the interface to use for scanning (enter the number): ").strip()
        if not selected_index.isdigit() or int(selected_index) < 0 or int(selected_index) >= len(interfaces):
            print("Invalid selection.")
            logging.error("Invalid Bluetooth interface selection.")
            return
    except ValueError:
        print("Invalid input. Please enter a valid number.")
        logging.error("Invalid input for Bluetooth interface selection.")
        return

    selected_interface = interfaces[int(selected_index)][0].strip(":")
    selected_bus_info = interfaces[int(selected_index)][1]
    print(f"Selected interface: {selected_interface} ({colored(selected_bus_info, 'magenta')})")

    try:
        update_mode = input("Select mode (1: No updates, 2: Update existing devices): ")
        if update_mode not in ('1', '2'):
            print("Invalid selection.")
            logging.error("Invalid update mode selection.")
            return
        update_mode = update_mode == '2'

        # Устанавливаем флаг начала сканирования
        utils.scanning_started = True

        # Регистрация функции сохранения словаря при выходе
        atexit.register(utils.save_device_last_count_update)

        asyncio.run(scan_ble_devices(selected_interface, update_mode))
    except KeyboardInterrupt:
        logging.info("Scan interrupted by user.")
        print("Scan interrupted by user.")

if __name__ == "__main__":
    main()

