# Basis-Image mit TensorFlow
FROM tensorflow/tensorflow:latest

# Arbeitsverzeichnis setzen
WORKDIR /app

# Kopiere alle Dateien ins Arbeitsverzeichnis
COPY . /app

# Aktualisiere pip auf die neueste Version
RUN python3 -m pip install --upgrade pip

# Installiere alle Abhängigkeiten aus requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

# Startkommando für den Container
CMD ["python", "server.py"]
