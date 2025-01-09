from flask import Flask, request, redirect, url_for, render_template, send_file
import os
import uuid
import shutil
import tensorflow as tf
import numpy as np
from tensorflow.keras.models import load_model
import paho.mqtt.publish as publish
import logging
import json
import zipfile
from datetime import datetime

# Ordnerpfade
UPLOAD_FOLDER = '/app/static/uploads'
LAST_IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, 'last_image')
MODEL_FOLDER = '/app/model'
DATASET_FOLDER = '/app/dataset'
STATE_FILE = '/app/state.txt'
LOCK_FILE = '/app/prediction.lock'
RETRAIN_LOCK = '/app/retrain.lock'
RETRAIN_LOG_FILE = '/app/retrain.log'
LOG_FILE = '/app/app.log'

# LOGGING
# Logger-Objekt erstellen
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Datei-Handler für Logging in Datei
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
# Stream-Handler für Console-Output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(file_formatter)
# Handlers hinzufügen
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Flask App initialisieren
app = Flask(__name__)

# Sicherstellen, dass die Ordner existieren
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LAST_IMAGE_FOLDER, exist_ok=True)  # Ordner für das letzte Bild
os.makedirs(os.path.join(DATASET_FOLDER, 'open'), exist_ok=True)
os.makedirs(os.path.join(DATASET_FOLDER, 'closed'), exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)

# MQTT-Konfiguration aus Umgebungsvariablen
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USER = os.getenv('MQTT_USER', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
RESULT_TOPIC = os.getenv('TOPIC', '')
CONFIG_TOPIC = os.getenv('CONFIG_TOPIC', '')
STATE_TOPIC = os.getenv('STATE_TOPIC', '')
SENSOR_NAME = os.getenv('SENSOR_NAME', '')
DEVICE_ID = os.getenv('DEVICE_ID', '')
DEVICE_NAME = os.getenv('DEVICE_NAME', '')
DEVICE_MODEL = os.getenv('DEVICE_MODEL', '')
DEVICE_MANUFACTURER = os.getenv('DEVICE_MANUFACTURER', '')


# Modellpfad
MODEL_PATH = os.path.join(MODEL_FOLDER, 'garage_door_model.keras')

# Modell initialisieren (global)
model = None
if os.path.exists(MODEL_PATH):
    try:
        logger.info(f"Lade Model von {MODEL_PATH} ...")
        model = load_model(MODEL_PATH)
        logger.info("Model erfolgreich geladen.")
    except Exception as e:
        logger.error(f"Fehler beim Laden des Modells: {e}")
else:
    logger.warning(f"Modellpfad {MODEL_PATH} existiert nicht.")

# Locking-Funktionen
def is_locked():
    return os.path.exists(LOCK_FILE)

def lock():
    open(LOCK_FILE, 'w').close()
    logger.info(f"Lock-Datei erstellt: {LOCK_FILE}")

def unlock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
        logger.info(f"Lock-Datei entfernt: {LOCK_FILE}")

def is_retraining():
    return os.path.exists(RETRAIN_LOCK)



CONFIG_PAYLOAD = {
    "name": SENSOR_NAME,
    "state_topic": STATE_TOPIC,
    "payload_on": "open",
    "payload_off": "closed",
    "device_class": "door",
    "unique_id": DEVICE_ID,
    "device": {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "model": DEVICE_MODEL,
        "manufacturer": DEVICE_MANUFACTURER
    }
}

def send_mqtt_discovery():
    try:
        logger.info("Sende MQTT Discovery-Konfiguration ...")
        publish.single(
            CONFIG_TOPIC,
            payload=json.dumps(CONFIG_PAYLOAD),
            retain=True,
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            auth={'username': MQTT_USER, 'password': MQTT_PASSWORD} if MQTT_USER else None
        )
        logger.info("MQTT Discovery-Konfiguration erfolgreich gesendet.")
    except Exception as e:
        logger.error(f"Fehler beim Senden der MQTT Discovery-Konfiguration: {e}")


def remove_old_locks():
    """Entfernt alte Lock-Dateien beim Start."""
    lock_files = [LOCK_FILE, RETRAIN_LOCK]
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info(f"Alte Lock-Datei entfernt: {lock_file}")

def remove_old_logs():
    """Entfernt alte Log-Dateien beim Start."""
    log_files = [RETRAIN_LOG_FILE, LOG_FILE]
    for log_file in log_files:
        if os.path.exists(log_file):
            logger.info(f"Alter Logname: {log_file}")
            logger.info(f"Alter Logpfad: {os.path.dirname(log_file)}")
            # Neuer Dateiname erstellen
            new_name = f"last_{os.path.basename(log_file)}"
            logger.info(f"Neuer Logname: {new_name}") 
            new_path = os.path.join(os.path.dirname(log_file), new_name)
            logger.info(f"Neuer Pfad für altes Log: {new_path}")
            # Datei umbenennen und entfernen
            os.rename(log_file, new_path)
            logger.info(f"Alte Log-Datei umbenannt: {log_file} -> {new_path}")
   #         os.remove(log_file)
   #         logger.info(f"Alte Log-Datei entfernt: {log_file}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Datei-Upload
        files = request.files.getlist('file')
        predictions = []

        for file in files:
            if file:
                filename = f"{uuid.uuid4()}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)

                # Letztes Bild aktualisieren
                for old_file in os.listdir(LAST_IMAGE_FOLDER):
                    os.remove(os.path.join(LAST_IMAGE_FOLDER, old_file))
                shutil.copy(filepath, LAST_IMAGE_FOLDER)

                # Automatische Vorhersage nur durchführen, wenn kein Lock existiert
                if not is_locked() and not is_retraining() and model:
                    lock()
                    try:
                        img = tf.keras.utils.load_img(filepath, target_size=(512, 896))
                        img_array = tf.keras.utils.img_to_array(img) / 255.0
                        img_array = tf.expand_dims(img_array, axis=0)

                        # Vorhersage durchführen
                        prediction = model.predict(img_array, batch_size=1)
                        predicted_class = "open" if prediction[0][0] > 0.5 else "closed"
                        predictions.append((filename, predicted_class))

                        # MQTT-Nachricht senden
                        try:
                            publish.single(
                                STATE_TOPIC,
                                payload=predicted_class,
                                retain=True,
                                hostname=MQTT_HOST,
                                port=MQTT_PORT,
                                auth={'username': MQTT_USER, 'password': MQTT_PASSWORD} if MQTT_USER else None
                            )
#                            logger.info(f"MQTT-Nachricht gesendet: {predicted_class}")
                            logger.info(f"MQTT-State: {predicted_class} wurde an {STATE_TOPIC} gesendet.")
                        except Exception as mqtt_error:
                            logger.error(f"Fehler beim Senden der MQTT-Nachricht: {mqtt_error}")

                        # Status in state.txt speichern
                        with open(STATE_FILE, 'w') as state_file:
                            state_file.write(predicted_class)

                    except Exception as e:
                        logger.error(f"Vorhersage fehlgeschlagen für {filename}: {e}")
                    finally:
                        unlock()

        return render_template('index.html', predictions=predictions, image_count=len(os.listdir(UPLOAD_FOLDER)))

    # Liste der Bilder anzeigen (nur gültige Bilddateien filtern)
    images = [
        image for image in os.listdir(UPLOAD_FOLDER)
        if os.path.isfile(os.path.join(UPLOAD_FOLDER, image)) and image.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    images.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)

    return render_template('index.html', images=images, image_count=len(images))

@app.route('/action/<action>/<path:filename>')
def action(action, filename):
    source = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(source):
        logger.error(f"Die Datei '{source}' wurde nicht gefunden.")
        return "Datei nicht gefunden", 404

    if action in ['open', 'closed']:
        dest = os.path.join(DATASET_FOLDER, action, os.path.basename(filename))
        try:
            shutil.move(source, dest)
            logger.info(f"Die Datei '{filename}' wurde nach '{dest}' verschoben.")
        except Exception as e:
            logger.error(f"Fehler beim Verschieben der Datei: {e}")
            return f"Fehler beim Verschieben der Datei: {e}", 500

    return redirect(url_for('index'))

@app.route('/retrain', methods=['POST'])
def retrain():
    if is_retraining():
        return "Retraining läuft bereits.", 409

    try:
        # Retraining-Lock setzen
        open(RETRAIN_LOCK, 'w').close()

        # Prüfen, ob ein altes Retrain-Log existiert
        if os.path.exists(RETRAIN_LOG_FILE):
            if not is_locked():  # Nur löschen, wenn kein Lock besteht
                os.remove(RETRAIN_LOG_FILE)

        # Starte das Retraining
        os.system(f'python retrain.py {MODEL_PATH} >> {RETRAIN_LOG_FILE} 2>&1 &')

        return redirect(url_for('last_prediction'))
    except Exception as e:
        logger.error(f"Error during retraining: {e}")
        return f"Error during retraining: {e}", 500
    finally:
        if os.path.exists(RETRAIN_LOCK):
            os.remove(RETRAIN_LOCK)

@app.route('/download_dataset', methods=['GET'])
def download_dataset():
    try:
        # Erstelle einen temporären Zip-Dateinamen basierend auf Datum und Uhrzeit
        zip_filename = f"dataset_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
        zip_filepath = os.path.join('/app', zip_filename)

        # Zip den Dataset-Ordner
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, dirs, files in os.walk(DATASET_FOLDER):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, DATASET_FOLDER)
                    zipf.write(file_path, arcname)

        # Sende die Datei zum Download
        return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)

    finally:
        # Entferne die Zip-Datei nach dem Download
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
            logging.info(f"Temporäre Zip-Datei gelöscht: {zip_filepath}")

@app.route('/delete_dataset', methods=['POST'])
def delete_dataset():
    try:
        for subfolder in ['open', 'closed']:
            folder_path = os.path.join(DATASET_FOLDER, subfolder)
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logging.info(f"Datei gelöscht: {file_path}")
        return "Dataset erfolgreich geleert.", 200
    except Exception as e:
        logging.error(f"Fehler beim Löschen des Dataset: {e}")
        return f"Fehler beim Löschen des Dataset: {e}", 500

@app.route('/last_prediction')
def last_prediction():
    global training_logs
    mqtt_status = "Not Sent"

    # Initialisiere `training_logs`
    if os.path.exists(RETRAIN_LOG_FILE):
        with open(RETRAIN_LOG_FILE, 'r') as log_file:
            training_logs = log_file.read()
    else:
        training_logs = "Keine Trainings-Logs vorhanden."

    # Modell überprüfen
    if model is None:
        prediction_error = "Das Modell konnte nicht geladen werden. Überprüfen Sie den Pfad oder die Modelldatei."
        return render_template('last_prediction.html', error=prediction_error, logs=training_logs)

    # Letztes Bild im LAST_IMAGE_FOLDER finden
    last_image_files = [
        image for image in os.listdir(LAST_IMAGE_FOLDER)
        if os.path.isfile(os.path.join(LAST_IMAGE_FOLDER, image)) and image.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    if not last_image_files:
        prediction_error = "Kein Bild im Ordner für das letzte Bild gefunden."
        return render_template('last_prediction.html', error=prediction_error, logs=training_logs)

    # Nehme das erste Bild im LAST_IMAGE_FOLDER
    last_image_path = os.path.join(LAST_IMAGE_FOLDER, last_image_files[0])

    # Vorhersage mit dem Modell
    try:
        img = tf.keras.utils.load_img(last_image_path, target_size=(512, 896))
        img_array = tf.keras.utils.img_to_array(img) / 255.0
        img_array = tf.expand_dims(img_array, axis=0)

        predictions = model.predict(img_array, batch_size=1)
        predicted_class = "open" if predictions[0][0] > 0.5 else "closed"
        mqtt_status = f"Success, Status sent: {str(predicted_class)}"
    except Exception as e:
        prediction_error = f"Error in prediction: {e}"
        logger.error(prediction_error)
        mqtt_status = f"Failed: {str(e)}"
        return render_template('last_prediction.html', error=prediction_error, logs=training_logs, mqtt_status=mqtt_status)

    return render_template('last_prediction.html', prediction=predicted_class, last_image=last_image_files[0], logs=training_logs, mqtt_status=mqtt_status)

@app.route('/logs')
def get_logs():
    if os.path.exists(RETRAIN_LOG_FILE):
        with open(RETRAIN_LOG_FILE, 'r') as log_file:
            logs = log_file.read()
    else:
        logs = "Keine Trainings-Logs vorhanden."
    return {"logs": logs}  # Rückgabe als JSON


@app.route('/download_model', methods=['GET'])
def download_model():
    try:
        model_path = MODEL_PATH
        if os.path.exists(model_path):
            return send_file(model_path, as_attachment=True, download_name="garage_door_model.keras")
        else:
            return "Model file not found", 404
    except Exception as e:
        logger.error(f"Error while downloading the model: {e}")
        return "Error while downloading the model", 500

if __name__ == '__main__':
    send_mqtt_discovery()
    remove_old_locks()
    remove_old_logs()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
