# main.py

import asyncio
import sys
import threading
import time
import logging
import argparse
from modules.gps_server import start_gps_server
from modules.bluetooth_scanner import get_bluetooth_interfaces, start_continuous_scan_and_connect
from modules.database import initialize_database
from modules import utils
from termcolor import colored

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

def main():
    parser = argparse.ArgumentParser(
        description="PiBLE Application: Always scan + connect, store GATT data in DB, and optionally use GPS.",
        epilog="No mode selection; the program automatically runs in continuous scanning+connecting mode."
    )
    parser.add_argument("--use-gps", choices=["y", "n"], help="Use GPS? 'y' to enable, 'n' to skip.")
    parser.add_argument("--adapter-index", type=int, help="Index of the Bluetooth adapter to use.")
    args = parser.parse_args()

    # Initialize the database
    initialize_database()

    # Prompt for GPS usage if not given
    if args.use_gps is None:
        use_gps_input = input("Use GPS? (y/n): ")
    else:
        use_gps_input = args.use_gps
    utils.use_gps = (use_gps_input.lower() == 'y')

    # Start GPS server if GPS is used
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

    # Find all Bluetooth interfaces
    interfaces = get_bluetooth_interfaces()
    if not interfaces:
        print("No Bluetooth interfaces found.")
        sys.exit(1)

    # Prompt or use CLI argument for adapter index
    if args.adapter_index is not None:
        adapter_index = args.adapter_index
    else:
        print("Available Bluetooth interfaces:")
        for idx, (interface, bus_info) in enumerate(interfaces):
            print(f"{idx}: {interface} ({bus_info})")
        adapter_index = int(input("Select the interface to use (enter the number): "))

    if adapter_index < 0 or adapter_index >= len(interfaces):
        print("Invalid adapter index.")
        sys.exit(1)

    chosen_adapter = interfaces[adapter_index][0]

    # Prompt for concurrency limit
    limit_input = input("Set the limit on the number of simultaneous connections: ")
    if limit_input.isdigit():
        utils.max_connect = int(limit_input)
    else:
        utils.max_connect = 5  # default

    # Start continuous scanning and connecting
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_continuous_scan_and_connect(chosen_adapter))
    except KeyboardInterrupt:
        print("[INFO] Keyboard interrupt received. Exiting.")
    finally:
        loop.close()

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
