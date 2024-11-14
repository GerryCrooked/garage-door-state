#!/bin/bash

MODEL_PATH="/app/model/garage_door_model.h5"

# Retrain das Modell
python /app/retrain.py $MODEL_PATH

# Optional: Wenn du die Datensätze nach dem Training leeren möchtest, entferne das Kommentarzeichen
# rm -rf /dataset/open/*
# rm -rf /dataset/closed/*
