import sqlite3

# Путь к базе данных
db_path = 'bluetooth_devices.db'

# Подключение к базе данных SQLite
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# UUID сервиса "Device Information"
device_info_uuid = "0000180a-0000-1000-8000-00805f9b34fb"

# Запрос строк, где service содержит "Device Information" и name равно "Unknown"
cursor.execute("""
    SELECT id, service, name
    FROM devices
    WHERE service LIKE ? AND name = "Unknown"
""", (f"%{device_info_uuid}%",))

rows_to_update = cursor.fetchall()

# Обработка каждой строки
for row in rows_to_update:
    device_id, service, _ = row

    # Инициализация переменных для хранения данных
    model_number, manufacturer_name = None, None

    # Извлечение Model Number String
    if "Model Number String" in service:
        start_index = service.find("Model Number String (UUID: ") + len("Model Number String (UUID: ")
        value_start = service.find("Value: bytearray(b'", start_index) + len("Value: bytearray(b'")
        value_end = service.find("')", value_start)
        model_number = service[value_start:value_end]
    
    # Извлечение Manufacturer Name String
    if "Manufacturer Name String" in service:
        start_index = service.find("Manufacturer Name String (UUID: ") + len("Manufacturer Name String (UUID: ")
        value_start = service.find("Value: bytearray(b'", start_index) + len("Value: bytearray(b'")
        value_end = service.find("')", value_start)
        manufacturer_name = service[value_start:value_end]

    # Обновление столбца name, если найдены обе характеристики
    if model_number and manufacturer_name:
        new_name = f"{model_number} {manufacturer_name}"
        cursor.execute("UPDATE devices SET name = ? WHERE id = ?", (new_name, device_id))

# Фиксация изменений и закрытие подключения
conn.commit()
conn.close()

print("База данных успешно обновлена.")


