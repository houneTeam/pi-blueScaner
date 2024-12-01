# modules/device_connector.py

import asyncio
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from .utils import is_mac_address
from .database import save_device_to_db
from termcolor import colored
import logging
from datetime import datetime
from . import utils  # Import utils to access the device_being_processed flag

devices_to_connect = asyncio.Queue()
devices_to_connect_helper = asyncio.Queue()  # Queue for helper

async def process_devices(adapter):
    while True:
        device = await devices_to_connect.get()
        try:
            print(f"{colored('[CONNECTING]', 'white')} {device.name} ({device.address}) using adapter {adapter}")
            async with BleakClient(device.address, adapter=adapter) as client:
                services = await client.get_services()
                device_info = ""
                services_list = []

                print(f"{colored('[CONNECTED!]', 'green')} {device.name} ({device.address})")
                for service in services:
                    service_data = f"Service: {service.uuid} - {service.description}"
                    characteristics = []
                    for char in service.characteristics:
                        properties = ', '.join(char.properties)
                        value = None
                        if 'read' in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                if service.uuid == '0000180a-0000-1000-8000-00805f9b34fb':
                                    device_info += f"Characteristic: {char.uuid} - Value: {value}; "
                                characteristics.append(f"Characteristic: {char.uuid} - Properties: {properties} - Value: {value}")
                            except Exception as e:
                                print(f'    Failed to read characteristic {char.uuid}: {e}')
                        else:
                            characteristics.append(f"Characteristic: {char.uuid} - Properties: {properties}")

                    service_data += " | Characteristics: " + "; ".join(characteristics)
                    services_list.append(service_data)
                
                device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_device_to_db(
                    device_name, device.address, None, timestamp, adapter,
                    manufacturer_data=None, service_uuids=None, service_data=None,
                    tx_power=None, platform_data=None, gps_data=None,
                    device_info=device_info.strip(), service_list='; '.join(services_list),
                    update_existing=True
                )
                print(f"{colored('[DEVICE UPDATED]', 'cyan')} {device_name} ({device.address})")
            print(f'Processed device: {device.name} ({device.address})')
        except Exception as e:
            print(f"{colored('[CONNECTION FAILED]', 'red')} {device.name} ({device.address}): {e}")
            logging.error(f'Failed to connect to {device.address} using adapter {adapter}: {e}')
        finally:
            devices_to_connect.task_done()
            utils.device_being_processed = False  # Reset the flag after processing
            await asyncio.sleep(1)

async def helper_process_devices(adapter):
    while True:
        device = await devices_to_connect_helper.get()
        try:
            print(f"{colored('[HELPER CONNECTING]', 'white')} {device.name} ({device.address}) using adapter {adapter}")
            async with BleakClient(device.address, adapter=adapter) as client:
                services = await client.get_services()
                device_info = ""
                services_list = []

                print(f"{colored('[HELPER CONNECTED!]', 'green')} {device.name} ({device.address})")
                for service in services:
                    service_data = f"Service: {service.uuid} - {service.description}"
                    characteristics = []
                    for char in service.characteristics:
                        properties = ', '.join(char.properties)
                        value = None
                        if 'read' in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                if service.uuid == '0000180a-0000-1000-8000-00805f9b34fb':
                                    device_info += f"Characteristic: {char.uuid} - Value: {value}; "
                                characteristics.append(f"Characteristic: {char.uuid} - Properties: {properties} - Value: {value}")
                            except Exception as e:
                                print(f'    Failed to read characteristic {char.uuid}: {e}')
                        else:
                            characteristics.append(f"Characteristic: {char.uuid} - Properties: {properties}")

                    service_data += " | Characteristics: " + "; ".join(characteristics)
                    services_list.append(service_data)
                
                device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_device_to_db(
                    device_name, device.address, None, timestamp, adapter,
                    manufacturer_data=None, service_uuids=None, service_data=None,
                    tx_power=None, platform_data=None, gps_data=None,
                    device_info=device_info.strip(), service_list='; '.join(services_list),
                    update_existing=True
                )
                print(f"{colored('[HELPER DEVICE UPDATED]', 'cyan')} {device_name} ({device.address})")
            print(f'Helper processed device: {device.name} ({device.address})')
        except Exception as e:
            print(f"{colored('[HELPER CONNECTION FAILED]', 'red')} {device.name} ({device.address}): {e}")
            logging.error(f'Helper failed to connect to {device.address} using adapter {adapter}: {e}')
        finally:
            devices_to_connect_helper.task_done()
            utils.device_being_processed = False  # Reset the flag after processing
            await asyncio.sleep(1)
