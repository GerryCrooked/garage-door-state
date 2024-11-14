from flask import Flask, request, redirect, url_for, render_template, send_file
import os
import uuid
import shutil
import time

app = Flask(__name__)

# Ordnerpfade
UPLOAD_FOLDER = 'static/uploads'
MODEL_FOLDER = 'model'
DATASET_FOLDER = '../dataset'

# Sicherstellen, dass die Ordner existieren
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(DATASET_FOLDER, 'open'), exist_ok=True)
os.makedirs(os.path.join(DATASET_FOLDER, 'closed'), exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Datei-Upload
        file = request.files['file']
        if file:
            filename = f"{uuid.uuid4()}.jpg"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            return redirect(url_for('index'))
    # Liste der Bilder
    images = os.listdir(UPLOAD_FOLDER)
    images.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)
    return render_template('index.html', images=images)

@app.route('/action/<action>/<filename>')
def action(action, filename):
    source = os.path.join(UPLOAD_FOLDER, filename)
    if action in ['open', 'closed']:
        dest = os.path.join(DATASET_FOLDER, action, filename)
        shutil.move(source, dest)
    return redirect(url_for('index'))

@app.route('/retrain', methods=['POST'])
def retrain():
    # Starte das Retraining
    os.system('./retrain.sh')
    return redirect(url_for('index'))

@app.route('/download_model')
def download_model():
    model_path = os.path.join(MODEL_FOLDER, 'garage_door_model.h5')
    if os.path.exists(model_path):
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        return send_file(model_path, as_attachment=True, download_name=f'garage_door_model_{timestamp}.h5')
    else:
        return "Modell nicht gefunden.", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
