#!/bin/bash

MODEL_PATH="/app/model/garage_door_model.keras"

# Sicherstellen, dass die Verzeichnisse existieren
if [ ! -d "/app/dataset/open" ] || [ ! -d "/app/dataset/closed" ]; then
    echo "Dataset-Verzeichnisse fehlen. Bitte überprüfe, ob die Verzeichnisse 'open' und 'closed' existieren."
    exit 1
fi

LOCK_FILE="/app/retrain.lock"

# Logfile bereinigen
RETRAIN_LOG="/app/retrain.log"
> "$RETRAIN_LOG"

# Retrain das Modell
python /app/retrain.py $MODEL_PATH

# Optional: Wenn du die Datensätze nach dem Training leeren möchtest, entferne das Kommentarzeichen
# rm -rf /dataset/open/*
# rm -rf /dataset/closed/*

