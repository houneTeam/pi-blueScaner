# device_connector.py

import asyncio
import logging
from datetime import datetime
from bleak import BleakClient
from termcolor import colored

# Import your DB helper so you can call save_device_to_db(...)
from .database import save_device_to_db, update_gatt_services
from .utils import is_mac_address
from . import utils

async def connect_to_device(device, adapter, semaphore):
    async with semaphore:
        try:
            async with BleakClient(device.address, adapter=adapter) as client:
                if client.is_connected:
                    device_name = device.name or "Unknown"
                    if is_mac_address(device_name):
                        device_name = "Unknown"

                    print(f"{colored('[CONNECTED]', 'green')} {device_name} ({device.address})")
                    logging.info(f"Connected to {device_name} ({device.address})")

                    services_data = []

                    # Gather GATT service info
                    for service in client.services:
                        service_info = f"Service: {service.uuid} - {service.description or 'No description'}"
                        services_data.append(service_info)

                        for char in service.characteristics:
                            char_info = f"  ├─ Characteristic: {char.uuid} - {char.description or 'No description'}"
                            services_data.append(char_info)

                            props = ", ".join(char.properties)
                            services_data.append(f"  │  Properties: {props}")

                            if "read" in char.properties:
                                try:
                                    value = await client.read_gatt_char(char)
                                    services_data.append(f"  │  Value: {value}")
                                except Exception as e:
                                    services_data.append(f"  │  Read error: {e}")

                            services_data.append("  └─────────────────────────────────")

                    # Convert the list of lines to one string
                    service_list_str = "\n".join(services_data)

                    # 1) Store data in a separate gatt_services table
                    update_gatt_services(device.address, service_list_str)

                    # 2) Also store it in the devices table’s "service" column
                    timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_device_to_db(
                        device_name, 
                        device.address,
                        rssi=None, 
                        timestamp=timestamp_now,
                        adapter=adapter,
                        manufacturer_data=None,
                        service_uuids=None,
                        service_data=None,
                        tx_power=None,
                        platform_data=None,
                        gps_data=None,
                        service_list=service_list_str,  # <-- This populates `devices.service`
                        update_existing=True             # <-- This tells the function to UPDATE if device exists
                    )

                    print(f"[DEVICE UPDATED] GATT data saved in both tables for {device.address}")
                    logging.info(f"GATT data saved for {device.address}")

        except Exception as e:
            print(f"[ERROR] Failed to connect to {device.address} on adapter {adapter}: {e}")
            logging.error(f"Failed to connect to {device.address} on adapter {adapter}: {e}")
        finally:
            await asyncio.sleep(1)

