import asyncio
import sys
import threading
import time
from modules.gps_server import start_gps_server
from modules.bluetooth_scanner import get_bluetooth_interfaces, scan_ble_devices
from modules.database import initialize_database
from modules import utils
from modules.device_connector import process_devices  # Removed helper_process_devices import
from termcolor import colored

def main():
    # Print logo
    logo = r'''                                       
    _/_/_/    _/  _/_/_/    _/        _/_/_/_/   
   _/    _/      _/    _/  _/        _/          
  _/_/_/    _/  _/_/_/    _/        _/_/_/       
 _/        _/  _/    _/  _/        _/            
_/        _/  _/_/_/    _/_/_/_/  _/_/_/_/                                                         
    '''
    print(colored(logo, 'blue'))
    print(colored('HouneTeam - PiBLE v0.2.0', 'white'))

    initialize_database()

    # Запускаем GPS сервер в отдельном потоке
    gps_thread = threading.Thread(target=start_gps_server)
    gps_thread.daemon = True
    gps_thread.start()

    # Ожидаем получения GPS данных
    print("Waiting for GPS data...")
    while not utils.gps_data_received:
        time.sleep(0.1)
    print("[INFO] GPS data received.")

    # Получаем список Bluetooth интерфейсов
    interfaces = get_bluetooth_interfaces()
    if not interfaces:
        print("No Bluetooth interfaces found.")
        sys.exit(1)

    # Выбор режима работы
    print("Select operation mode:")
    print("1: Scan only (single adapter)")
    print("2: Scan and connect (two adapters required)")
    mode = input("Enter mode number: ")

    if mode == "1":
        utils.connect_mode = False
        # Выбираем интерфейс для сканирования
        print("Available Bluetooth interfaces:")
        for idx, (interface, bus_info) in enumerate(interfaces):
            print(f"{idx}: {interface} ({bus_info})")
        scan_adapter_idx = int(input("Select the interface to use for scanning (enter the number): "))
        scan_adapter = interfaces[scan_adapter_idx][0]
        update_mode = input("Select mode (1: No updates, 2: Update existing devices): ")
        update_mode = update_mode == "2"

        # Вопрос об использовании помощника
        helper_mode_input = input("Use scanning adapter as helper for known devices? (y/n): ")
        helper_mode = helper_mode_input.lower() == 'y'

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [scan_ble_devices(scan_adapter, update_mode, helper_mode)]
        loop.run_until_complete(asyncio.gather(*tasks))
    elif mode == "2":
        utils.connect_mode = True
        # Выбираем интерфейсы для сканирования и подключения
        print("Available Bluetooth interfaces:")
        for idx, (interface, bus_info) in enumerate(interfaces):
            print(f"{idx}: {interface} ({bus_info})")
        scan_adapter_idx = int(input("Select the interface to use for scanning (enter the number): "))
        connect_adapter_idx = int(input("Select the interface to use for connecting (enter the number): "))

        if scan_adapter_idx == connect_adapter_idx:
            print("Scan and connect adapters must be different.")
            sys.exit(1)

        scan_adapter = interfaces[scan_adapter_idx][0]
        connect_adapter = interfaces[connect_adapter_idx][0]
        update_mode = input("Select mode (1: No updates, 2: Update existing devices): ")
        update_mode = update_mode == "2"

        # Вопрос об использовании помощника
        helper_mode_input = input("Use scanning adapter as helper for known devices? (y/n): ")
        helper_mode = helper_mode_input.lower() == 'y'

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [
            scan_ble_devices(scan_adapter, update_mode, helper_mode),
            process_devices(connect_adapter)
        ]
        loop.run_until_complete(asyncio.gather(*tasks))
    else:
        print("Invalid mode selected.")
        sys.exit(1)

if __name__ == "__main__":
    main()
