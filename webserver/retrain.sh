#!/bin/bash

# Pfade anpassen
DATASET_OPEN="/dataset/open"
DATASET_CLOSED="/dataset/closed"
MODEL_PATH="/app/model/garage_door_model.keras"

# Retrain das Modell
python /app/retrain.py $DATASET_OPEN $DATASET_CLOSED $MODEL_PATH

# Neustart des Image Analyzer Containers
docker-compose restart image_analyzer

# Leere den Dataset-Ordner
rm -rf $DATASET_OPEN/*
rm -rf $DATASET_CLOSED/*