from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import paho.mqtt.client as mqtt
import json
import os
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# MQTT-Konfiguration
MQTT_BROKER = os.getenv("MQTT_BROKER")  # IP-Adresse des MQTT-Brokers (aus .env-Datei)
MQTT_PORT = 1883
CONFIG_TOPIC = "homeassistant/sensor/garage_door_status/config"
STATE_TOPIC = "homeassistant/sensor/garage_door_status/state"

# Flask-App und Modell laden
app = Flask(__name__)
MODEL_PATH = "/app/garage_door_model.keras"
model = tf.keras.models.load_model(MODEL_PATH)

# MQTT-Client initialisieren
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

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

# Sende Konfigurationsnachricht für Discovery
mqtt_client.publish(CONFIG_TOPIC, json.dumps(config_payload), retain=True)

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
