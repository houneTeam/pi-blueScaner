# modules/gps_server.py

from flask import Flask, request, jsonify
import threading
import time
from termcolor import colored
from . import utils  # Импортируем utils для доступа к глобальным переменным и функциям
import logging

app = Flask(__name__)

# Подавляем логирование запросов Flask
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Создаем событие для сигнализации о получении GPS-данных
gps_data_received_event = threading.Event()

def update_gps_status():
    """Обновляет gps_status на основе актуальности GPS-данных."""
    while True:
        if utils.is_gps_data_fresh():
            utils.gps_status = "online"
        else:
            utils.gps_status = "offline"
        time.sleep(1)

@app.route('/gps', methods=['POST'])
def receive_gps():
    data = request.get_json()
    if data:
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        utils.latest_gps_coords["latitude"] = latitude
        utils.latest_gps_coords["longitude"] = longitude
        utils.last_gps_update_time = time.time()
        # Сигнализируем о получении GPS-данных
        gps_data_received_event.set()
        # Выводим [GPS DATA] только если сканирование началось
        if utils.scanning_started:
            print(f"{colored('[GPS DATA]', 'cyan')} Current Coordinates: {latitude}, {longitude}")
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

@app.route('/gps', methods=['GET'])
def gps_status_route():
    return jsonify({"status": utils.gps_status}), 200

def start_gps_server():
    print(f"{colored('[INFO]', 'blue')} GPS server online.")
    # Запускаем поток для обновления gps_status
    threading.Thread(target=update_gps_status, daemon=True).start()
    app.run(host='192.168.4.1', port=5000, debug=False, use_reloader=False)

