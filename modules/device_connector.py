import asyncio
from bleak import BleakClient, BleakError
from bleak.uuids import uuidstr_to_str
from .database import save_device_to_db
from termcolor import colored
from datetime import datetime
from .utils import is_mac_address
import logging
from . import utils

async def connect_to_device(device, adapter):
    """Подключается к устройству, получает сервисы/характеристики и сохраняет в БД."""
    try:
        print(f"Using adapter: {adapter}")
        print(f"{colored('[CONNECTING]', 'white')} {device.name} ({device.address})")
        async with BleakClient(device.address, adapter=adapter) as client:
            if client.is_connected:
                print(f"\n{colored('[CONNECTED]', 'green')} {device.name or 'Unknown'} ({device.address})")
                print("Retrieving services and characteristics...")

                services_list = []
                services = await client.get_services()
                for service in services:
                    service_name = uuidstr_to_str(service.uuid) or "Unknown Service"
                    service_desc = service.description if service.description else "No description"
                    service_info = f"Service: {service_name} (UUID: {service.uuid}) - {service_desc}"
                    services_list.append(service_info)
                    print(service_info)
                    for char in service.characteristics:
                        char_name = uuidstr_to_str(char.uuid) or "Unknown Characteristic"
                        char_desc = char.description if char.description else "No description"
                        properties = ", ".join(char.properties)
                        char_info = f"  ├─ Characteristic: {char_name} (UUID: {char.uuid}) - {char_desc}"
                        services_list.append(char_info)
                        print(char_info)
                        print(f"  │  Properties: {properties}")
                        services_list.append(f"  │  Properties: {properties}")

                        if "read" in char.properties:
                            try:
                                value = await client.read_gatt_char(char)
                                char_value = f"  │  Value: {value}"
                                services_list.append(char_value)
                                print(char_value)
                            except Exception as e:
                                error_str = f"  │  Read error: {e}"
                                print(error_str)
                                services_list.append(error_str)
                        else:
                            print("  │  Skipped, no read property")
                            services_list.append("  │  Skipped, no read property")

                        print("  └─────────────────────────────────")
                        services_list.append("  └─────────────────────────────────")

                # Сохраняем полученные сервисы и характеристики в БД
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                device_name = device.name if device.name and not is_mac_address(device.name) else "Unknown"

                save_device_to_db(
                    device_name, device.address, None, timestamp, adapter,
                    manufacturer_data=None, service_uuids=None, service_data=None,
                    tx_power=None, platform_data=None, gps_data=None,
                    service_list="\n".join(services_list),
                    update_existing=True
                )
                print(f"{colored('[DEVICE UPDATED]', 'cyan')} Info saved in DB for {device.address}")

    except BleakError as e:
        print(f"{colored('[CONNECTION FAILED]', 'red')} {device.name} ({device.address}): {e}")
        logging.error(f'Failed to connect to {device.address} using adapter {adapter}: {e}')
    except Exception as e:
        print(f"{colored('[ERROR]', 'red')} Unexpected error: {e}")
        logging.error(f'Unexpected error when connecting to {device.address} using adapter {adapter}: {e}')
    finally:
        await asyncio.sleep(1)
