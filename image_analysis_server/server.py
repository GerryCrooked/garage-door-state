@app.route("/analyze", methods=["POST"])
def analyze_image():
    # Prüfen, ob ein Bild gesendet wurde
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    # Lade das Bild aus dem Upload als BytesIO-Objekt
    file = request.files['file']
    img = image.load_img(BytesIO(file.read()), target_size=(224, 224))
    
    # Bild in ein Numpy-Array konvertieren und skalieren
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0

    # Vorhersage
    prediction = model.predict(img_array)
    probability = prediction[0][0]  # Annahme: Das Modell gibt eine Wahrscheinlichkeit für "open" zurück
    status = "open" if probability > 0.5 else "closed"

    # Logge die Vorhersagewahrscheinlichkeit, Entscheidung und HTTP-Anfrage im Log
    log_message = f"POST /analyze - Entscheidung: {status}, Vorhersagewahrscheinlichkeit: {probability:.2f}"
    print(log_message)
    logging.info(log_message)

    # Ergebnis über MQTT senden (als Text und mit retain=True)
    mqtt_client.publish(STATE_TOPIC, status, retain=True)

    # Ergebnis als Antwort zurückgeben
    return jsonify({"status": status, "probability": probability})
