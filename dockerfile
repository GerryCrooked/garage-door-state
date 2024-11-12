
FROM tensorflow/tensorflow:latest

WORKDIR /app

COPY . /app

RUN pip install --ignore-installed flask pillow numpy paho-mqtt

CMD ["python", "server.py"]
