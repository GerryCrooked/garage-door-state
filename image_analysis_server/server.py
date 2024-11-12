from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import paho.mqtt.client as mqtt
import json
import os
import logging
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# MQTT-Konfiguration aus Umgebungsvariablen
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
CONFIG_TOPIC = "homeassistant/sensor/garage_door_status/config"
STATE_TOPIC = "homeassistant/sensor/garage_door_status/state"

# Logging-Konfiguration für Fehlerprotokoll
logging.basicConfig(filename='connection.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Flask-App und Modell laden
app = Flask(__name__)
MODEL_PATH = "/app/garage_door_model.keras"
model = tf.keras.models.load_model(MODEL_PATH)

# MQTT-Client initialisieren und Konfigurationsnachricht festlegen
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Callback für die Verbindung
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Verbindung zum MQTT-Broker erfolgreich.")
    else:
        print(f"Verbindung zum MQTT-Broker fehlgeschlagen. Fehlercode: {rc}")
        logging.error(f"Verbindung zum MQTT-Broker fehlgeschlagen. Fehlercode: {rc}")

# Callback für das Veröffentlichen
def on_publish(client, userdata, mid):
    print("Nachricht erfolgreich veröffentlicht.")

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
    "unit_of_measurement": "",
    "value_template": "{{ value_json.status }}",
    "unique_id": "garage_door_status_sensor",
    "device": {
        "identifiers": ["garage_door_sensor"],
        "name": "Garage Door Sensor",
        "model": "Custom Model",
        "manufacturer": "Your Company"
    }
}

# Sende die Konfigurationsnachricht für Discovery
mqtt_client.loop_start()
mqtt_client.publish(CONFIG_TOPIC, json.dumps(config_payload), retain=True)
mqtt_client.loop_stop()

@app.route("/analyze", methods=["POST"])
def analyze_image():
    # Prüfen, ob ein Bild gesendet wurde
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    # Bild vorbereiten
    img = image.load_img(request.files['file'], target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0

    # Vorhersage
    prediction = model.predict(img_array)
    status = "open" if prediction[0] > 0.5 else "closed"

    # Ergebnis über MQTT senden
    mqtt_client.publish(STATE_TOPIC, json.dumps({"status": status}))

    # Ergebnis als Antwort zurückgeben
    return jsonify({"status": status})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
