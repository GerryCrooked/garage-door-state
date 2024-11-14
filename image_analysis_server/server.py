import os
import tensorflow as tf
import numpy as np
import paho.mqtt.client as mqtt
from PIL import Image
import io

# MQTT-Konfiguration aus Umgebungsvariablen
MQTT_HOST = os.environ.get('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_USER = os.environ.get('MQTT_USER', '')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
IMAGE_TOPIC = os.environ.get('IMAGE_TOPIC', 'image_topic')
RESULT_TOPIC = os.environ.get('RESULT_TOPIC', 'result_topic')

MODEL_PATH = '/app/model/garage_door_model.h5'

print("TensorFlow Version:", tf.__version__)
print("Keras Version:", tf.keras.__version__)

# Modell laden
model = tf.keras.models.load_model(MODEL_PATH)

# MQTT-Client initialisieren
client = mqtt.Client()

if MQTT_USER and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

def on_connect(client, userdata, flags, rc):
    print("Verbunden mit MQTT Broker")
    client.subscribe(IMAGE_TOPIC)

def on_message(client, userdata, msg):
    print(f"Nachricht erhalten auf Thema {msg.topic}")
    image_data = msg.payload
    image = Image.open(io.BytesIO(image_data)).convert('RGB')
    image = image.resize((180, 180))
    image_array = np.expand_dims(np.array(image) / 255.0, axis=0)

    prediction = model.predict(image_array)
    result = 'open' if prediction[0][0] > 0.5 else 'closed'
    print(f"Erkannter Zustand: {result}")

    client.publish(RESULT_TOPIC, result)

client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_forever()
