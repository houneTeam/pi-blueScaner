import asyncio
import sys
import threading
import time
import logging
import argparse
from modules.gps_server import start_gps_server
from modules.bluetooth_scanner import get_bluetooth_interfaces, scan_ble_devices
from modules.database import initialize_database
from modules import utils
from termcolor import colored

# Настраиваем логгирование в файл app.log
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

def main():
    parser = argparse.ArgumentParser(
        description="PiBLE Application: Scan BLE devices, optionally connect and retrieve GATT data, integrate with GPS.",
        epilog="If no arguments are provided, the program runs interactively."
    )
    parser.add_argument("--use-gps", choices=["y", "n"], help="Use GPS? 'y' to start GPS server and wait for data, 'n' to skip GPS usage.")
    parser.add_argument("--mode", type=int, choices=[1,2],
                        help="Select operation mode: '1' for scan only (single adapter), '2' for scan and connect (two adapters).")
    parser.add_argument("--scan-adapter", type=int, 
                        help="Index of the adapter to use for scanning. Use 'hciconfig' or program output to see available adapters.")
    parser.add_argument("--connect-adapter", type=int, 
                        help="Index of the adapter to use for connecting (only if mode=2). Must be different from scan adapter.")
    parser.add_argument("--update-mode", choices=["1","2"], 
                        help="Select database update mode: '1' for no updates of existing records, '2' to update existing devices.")
    parser.add_argument("--helper-mode", choices=["y","n"], 
                        help="Use scanning adapter as a helper for known devices? 'y' to enable, 'n' to disable.")
    parser.add_argument("--max-connect", type=int, 
                        help="Maximum number of devices to connect at once (only if mode=2).")

    args = parser.parse_args()

    initialize_database()

    # Вопрос о использовании GPS
    if args.use_gps is None:
        use_gps_input = input("Use GPS? (y/n): ")
    else:
        use_gps_input = args.use_gps
    utils.use_gps = (use_gps_input.lower() == 'y')

    if utils.use_gps:
        gps_thread = threading.Thread(target=start_gps_server)
        gps_thread.daemon = True
        gps_thread.start()

        print("Waiting for GPS data...")
        while not utils.gps_data_received:
            time.sleep(0.1)
        print("[INFO] GPS data received.")
    else:
        utils.gps_status = "offline"
        utils.gps_data_received = True

    interfaces = get_bluetooth_interfaces()
    if not interfaces:
        print("No Bluetooth interfaces found.")
        sys.exit(1)

    # Выбор режима работы
    if args.mode is None:
        print("Select operation mode:")
        print("1: Scan only (single adapter)")
        print("2: Scan and connect (two adapters required)")
        mode = input("Enter mode number: ")
    else:
        mode = str(args.mode)

    if mode == "1":
        utils.connect_mode = False
        # Выбор интерфейса для сканирования
        if args.scan_adapter is None:
            print("Available Bluetooth interfaces:")
            for idx, (interface, bus_info) in enumerate(interfaces):
                print(f"{idx}: {interface} ({bus_info})")
            scan_adapter_idx = int(input("Select the interface to use for scanning (enter the number): "))
        else:
            scan_adapter_idx = args.scan_adapter
        scan_adapter = interfaces[scan_adapter_idx][0]

        if args.update_mode is None:
            update_mode_input = input("Select mode (1: No updates, 2: Update existing devices): ")
        else:
            update_mode_input = args.update_mode
        update_mode = (update_mode_input == "2")

        if args.helper_mode is None:
            helper_mode_input = input("Use scanning adapter as helper for known devices? (y/n): ")
        else:
            helper_mode_input = args.helper_mode
        helper_mode = helper_mode_input.lower() == 'y'

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [scan_ble_devices(scan_adapter, update_mode, helper_mode=helper_mode, connect_adapter=False)]
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except KeyboardInterrupt:
            print("[INFO] Keyboard interrupt received. Exiting.")

    elif mode == "2":
        utils.connect_mode = True

        if args.scan_adapter is None or args.connect_adapter is None:
            print("Available Bluetooth interfaces:")
            for idx, (interface, bus_info) in enumerate(interfaces):
                print(f"{idx}: {interface} ({bus_info})")

        if args.scan_adapter is None:
            scan_adapter_idx = int(input("Select the interface to use for scanning (enter the number): "))
        else:
            scan_adapter_idx = args.scan_adapter

        if args.connect_adapter is None:
            connect_adapter_idx = int(input("Select the interface to use for connecting (enter the number): "))
        else:
            connect_adapter_idx = args.connect_adapter

        if scan_adapter_idx == connect_adapter_idx:
            print("Scan and connect adapters must be different.")
            sys.exit(1)

        scan_adapter = interfaces[scan_adapter_idx][0]
        connect_adapter = interfaces[connect_adapter_idx][0]

        if args.update_mode is None:
            update_mode_input = input("Select mode (1: No updates, 2: Update existing devices): ")
        else:
            update_mode_input = args.update_mode
        update_mode = (update_mode_input == "2")

        if args.helper_mode is None:
            helper_mode_input = input("Use scanning adapter as helper for known devices? (y/n): ")
        else:
            helper_mode_input = args.helper_mode
        helper_mode = helper_mode_input.lower() == 'y'

        if args.max_connect is None:
            max_connect = int(input("Enter the maximum number of devices to connect at once: "))
        else:
            max_connect = args.max_connect
        utils.max_connect = max_connect

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [
            scan_ble_devices(scan_adapter, update_mode, helper_mode=False, connect_adapter=False),
            scan_ble_devices(connect_adapter, update_mode, helper_mode=helper_mode, connect_adapter=True)
        ]
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except KeyboardInterrupt:
            print("[INFO] Keyboard interrupt received. Exiting.")
    else:
        print("Invalid mode selected.")
        sys.exit(1)

if __name__ == "__main__":
    logo = r'''
    _/_/_/    _/  _/_/_/    _/        _/_/_/_/
   _/    _/      _/    _/  _/        _/
  _/_/_/    _/  _/_/_/    _/        _/_/_/
 _/        _/  _/    _/  _/        _/
_/        _/  _/_/_/    _/_/_/_/  _/_/_/_/
    '''
    print(colored(logo, 'blue'))
    print(colored('HouneTeam - PiBLE v0.2.0', 'white'))
    main()
