#!/bin/bash

# Retrain das Modell
python /app/retrain.py /dataset/open /dataset/closed /app/model/garage_door_model.keras

# Neustart des Image Analyzer Containers
docker-compose restart image_analyzer

# Leere den Dataset-Ordner
rm -rf /dataset/open/*
rm -rf /dataset/closed/*
