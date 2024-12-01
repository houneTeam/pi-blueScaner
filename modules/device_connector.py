import asyncio
from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak.uuids import uuidstr_to_str
from .database import save_device_to_db
from termcolor import colored
from datetime import datetime
from .utils import is_mac_address
import logging
from . import utils  # Import utils to access the device_being_processed flag

devices_to_connect = asyncio.Queue()

async def read_characteristic(client, characteristic):
    if "read" in characteristic.properties:
        try:
            value = await client.read_gatt_char(characteristic.uuid)
            return value
        except BleakError:
            return None
    return None

async def process_devices(adapter):
    while True:
        device = await devices_to_connect.get()
        utils.device_being_processed = True  # Set the flag
        try:
            print(f"Using adapter: {adapter}")
            print(f"{colored('[CONNECTING]', 'white')} {device.name} ({device.address})")
            async with BleakClient(device.address, adapter=adapter) as client:
                print("Connected to device.")
                print("Retrieving services...")
                services = await client.get_services()
                services_list = []
                for service in services:
                    service_name = uuidstr_to_str(service.uuid) or "Unknown Service"
                    service_data = f"Service: {service_name} (UUID: {service.uuid})"
                    characteristics = []
                    for characteristic in service.characteristics:
                        char_name = uuidstr_to_str(characteristic.uuid) or "Unknown Characteristic"
                        value = await read_characteristic(client, characteristic)
                        if value is not None:
                            characteristics.append(f"Characteristic: {char_name} (UUID: {characteristic.uuid}) - Value: {value}")
                        else:
                            characteristics.append(f"Skipped non-readable characteristic: {char_name} (UUID: {characteristic.uuid})")
                    service_data += " | Characteristics: " + "; ".join(characteristics)
                    services_list.append(service_data)
                service_list_str = "; ".join(services_list)

                device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_device_to_db(
                    device_name, device.address, None, timestamp, adapter,
                    manufacturer_data=None, service_uuids=None, service_data=None,
                    tx_power=None, platform_data=None, gps_data=None,
                    service_list=service_list_str,
                    update_existing=True
                )
                print(f"{colored('[DEVICE UPDATED]', 'cyan')} {device_name} ({device.address})")
        except BleakError as e:
            print(f"{colored('[CONNECTION FAILED]', 'red')} {device.name} ({device.address}): {e}")
            logging.error(f'Failed to connect to {device.address} using adapter {adapter}: {e}')
        except Exception as e:
            print(f"{colored('[ERROR]', 'red')} Unexpected error: {e}")
            logging.error(f'Unexpected error when connecting to {device.address} using adapter {adapter}: {e}')
        finally:
            devices_to_connect.task_done()
            utils.device_being_processed = False  # Reset the flag after processing
            await asyncio.sleep(1)
