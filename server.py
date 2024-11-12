from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import os

app = Flask(__name__)

# Modell laden
MODEL_PATH = "garage_door_model.keras"
model = tf.keras.models.load_model(MODEL_PATH)

@app.route("/analyze", methods=["POST"])
def analyze_image():
    # Prüfe, ob ein Bild gesendet wurde
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    # Bild laden
    img = image.load_img(request.files['file'], target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0

    # Vorhersage
    prediction = model.predict(img_array)
    status = "open" if prediction[0] > 0.5 else "closed"

    # Ergebnis zurückgeben
    return jsonify({"status": status})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
