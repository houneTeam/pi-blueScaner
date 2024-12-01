# modules/gps_server.py

from flask import Flask, request, jsonify
import threading
import time
from termcolor import colored
from . import utils  # Import utils for access to global variables and functions
import logging

app = Flask(__name__)

# Get logger for this module
logger = logging.getLogger(__name__)

# Suppress Flask request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def update_gps_status():
    """Updates gps_status based on freshness of GPS data."""
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
        # Signal that GPS data has been received
        utils.gps_data_received = True
        logger.info(f"Received GPS data: Latitude={latitude}, Longitude={longitude}")
        # Display GPS data only if scanning has started
        if utils.scanning_started:
            print(f"{colored('[GPS DATA]', 'cyan')} Current Coordinates: {latitude}, {longitude}")
        return jsonify({"status": "success"}), 200
    else:
        logger.warning("Received invalid GPS data.")
        return jsonify({"status": "error", "message": "Invalid data"}), 400

@app.route('/gps', methods=['GET'])
def gps_status_route():
    return jsonify({"status": utils.gps_status}), 200

def start_gps_server():
    print("GPS server is starting...")
    logger.info("GPS server started.")
    # Start thread to update gps_status
    threading.Thread(target=update_gps_status, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

