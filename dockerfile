
FROM tensorflow/tensorflow:latest

WORKDIR /app

COPY . /app

RUN pip install --ignore-installed flask pillow numpy paho-mqtt python-dotenv

CMD ["python", "server.py"]
