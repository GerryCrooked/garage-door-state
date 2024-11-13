from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import paho.mqtt.client as mqtt
import json
import os
import logging
from dotenv import load_dotenv
from io import BytesIO

# .env-Datei laden
load_dotenv()

# Flask-Anwendung initialisieren
app = Flask(__name__)

# MQTT-Konfiguration aus Umgebungsvariablen
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
DEVICE_MODEL = os.getenv("DEVICE_MODEL", "Default Model")
DEVICE_MANUFACTURER = os.getenv("DEVICE_MANUFACTURER", "Default Manufacturer")
CONFIG_TOPIC = "homeassistant/sensor/garage_door_status/config"
STATE_TOPIC = "homeassistant/sensor/garage_door_status/state"

# Logging-Konfiguration für Fehlerprotokoll
logging.basicConfig(filename='connection.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Modell laden
MODEL_PATH = "/app/garage_door_model.keras"
model = tf.keras.models.load_model(MODEL_PATH)

# MQTT-Client initialisieren und Konfigurationsnachricht festlegen
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Callback für die Verbindung
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Verbindung zum MQTT-Broker erfolgreich.")
        logging.info("Verbindung zum MQTT-Broker erfolgreich.")
    else:
        print(f"Verbindung zum MQTT-Broker fehlgeschlagen. Fehlercode: {rc}")
        logging.error(f"Verbindung zum MQTT-Broker fehlgeschlagen. Fehlercode: {rc}")

# Callback für das Veröffentlichen
def on_publish(client, userdata, mid):
    print("Nachricht erfolgreich veröffentlicht.")
    logging.info("Nachricht erfolgreich veröffentlicht.")

# Callback und Verbindung einstellen
mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish

try:
    # Versuche, eine Verbindung zum Broker herzustellen
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
except Exception as e:
    print("Fehler bei der Verbindung zum MQTT-Broker:", str(e))
    logging.error("Fehler bei der Verbindung zum MQTT-Broker: " + str(e))

# Konfigurationsnachricht für MQTT Discovery
config_payload = {
    "name": "Garagentor Status",
    "state_topic": STATE_TOPIC,
    "payload_on": "open",
    "payload_off": "closed",
    "unique_id": "garage_door_status_sensor",
    "device": {
        "identifiers": ["garage_door_sensor"],
        "name": "Garage Door Sensor",
        "model": DEVICE_MODEL,
        "manufacturer": DEVICE_MANUFACTURER
    }
}

# Sende die Konfigurationsnachricht an MQTT Discovery
mqtt_client.loop_start()
mqtt_client.publish(CONFIG_TOPIC, json.dumps(config_payload), retain=True)
mqtt_client.loop_stop()

@app.route("/analyze", methods=["POST"])
def analyze_image():
    # Prüfen, ob ein Bild gesendet wurde
    if 'file' not in request.files:
        logging.error("No file provided in the request.")
        return jsonify({"error": "No file provided"}), 400

    # Lade das Bild aus dem Upload als BytesIO-Objekt
    try:
        file = request.files['file']
        img = image.load_img(BytesIO(file.read()), target_size=(224, 224))
    except Exception as e:
        logging.error(f"Error loading image: {str(e)}")
        return jsonify({"error": "Failed to load image"}), 500

    # Bild in ein Numpy-Array konvertieren und skalieren
    try:
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0
    except Exception as e:
        logging.error(f"Error processing image array: {str(e)}")
        return jsonify({"error": "Failed to process image"}), 500

    # Vorhersage
    try:
        prediction = model.predict(img_array)
        probability = prediction[0][0]  # Annahme: Das Modell gibt eine Wahrscheinlichkeit für "open" zurück
        status = "open" if probability > 0.5 else "closed"
        log_message = f"POST /analyze - Entscheidung: {status}, Vorhersagewahrscheinlichkeit: {probability:.2f}"
        print(log_message)
        logging.info(log_message)
    except Exception as e:
        logging.error(f"Error during model prediction: {str(e)}")
        return jsonify({"error": "Model prediction failed"}), 500

    # MQTT-Veröffentlichung
    try:
        mqtt_client.publish(STATE_TOPIC, status, retain=True)
    except Exception as e:
        logging.error(f"Error publishing MQTT message: {str(e)}")
        return jsonify({"error": "Failed to publish MQTT message"}), 500

    # Ergebnis als Antwort zurückgeben
    try:
        return jsonify({"status": status, "probability": probability})
    except Exception as e:
        logging.error(f"Error returning response: {str(e)}")
        return jsonify({"error": "Failed to return response"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
