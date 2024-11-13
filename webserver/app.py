from flask import Flask, request, redirect, url_for, render_template
import os
import uuid
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
DATASET_FOLDER = '../dataset'

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
    return render_template('index.html', images=images)

@app.route('/action/<action>/<filename>')
def action(action, filename):
    source = os.path.join(UPLOAD_FOLDER, filename)
    if action in ['open', 'closed']:
        dest = os.path.join(DATASET_FOLDER, action, filename)
        shutil.move(source, dest)
    elif action == 'retrain':
        os.system('./retrain.sh')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
