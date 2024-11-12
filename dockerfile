
FROM tensorflow/tensorflow:latest

WORKDIR /app

COPY . /app

RUN pip install flask pillow numpy

CMD ["python", "server.py"]
