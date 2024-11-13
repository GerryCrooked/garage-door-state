FROM tensorflow/tensorflow:latest

WORKDIR /app

COPY . /app

RUN python3 -m pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python", "server.py"]
