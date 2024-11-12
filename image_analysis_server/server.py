from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import paho.mqtt.client as mqtt

# MQTT-Konfiguration
MQTT_BROKER = ${MQTT_BROKER}  # IP-Adresse des MQTT-Brokers (Home Assistant)
MQTT_PORT = 1883
MQTT_TOPIC = "homeassistant/garage/door_status"

# Flask-App und Modell laden
app = Flask(__name__)
MODEL_PATH = "/app/garage_door_model.keras"
model = tf.keras.models.load_model(MODEL_PATH)

# MQTT-Client initialisieren
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

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
    mqtt_client.publish(MQTT_TOPIC, status)

    # Ergebnis als Antwort zurückgeben
    return jsonify({"status": status})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
