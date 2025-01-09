# -*- coding: utf-8 -*-
import os
import time
import logging

# Konfiguration
UPLOAD_FOLDER = '/app/static/uploads'
DATASET_FOLDER = '/app/dataset'
DAYS_TO_KEEP_UNCAT = int(os.environ.get('DAYS_TO_KEEP_UNCAT', 1))
DAYS_TO_KEEP_DATASET = int(os.environ.get('DAYS_TO_KEEP_DATASET', 30))
LOG_FILE = '/app/cleanup.log'

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def cleanup_old_files(folder, days):
    """Löscht Dateien, die älter als die angegebene Anzahl von Tagen sind."""
    now = time.time()
    cutoff = now - (days * 86400)  # 86400 Sekunden = 1 Tag
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff:
                logging.info(f"Lösche Datei: {file_path}")
                os.remove(file_path)


def cleanup():
    """Führt den vollständigen Cleanup-Prozess aus."""
    # Cleanup für nicht kategorisierte Bilder
    logging.info("Starte Cleanup für nicht kategorisierte Bilder...")
    cleanup_old_files(UPLOAD_FOLDER, DAYS_TO_KEEP_UNCAT)

    # Cleanup für kategorisierte Bilder im Dataset
    logging.info("Starte Cleanup für Dataset...")
    cleanup_old_files(os.path.join(DATASET_FOLDER, 'open'), DAYS_TO_KEEP_DATASET)
    cleanup_old_files(os.path.join(DATASET_FOLDER, 'closed'), DAYS_TO_KEEP_DATASET)


if __name__ == "__main__":
    logging.info("Starte Cleanup-Prozess")
    try:
        cleanup()
        logging.info("Cleanup abgeschlossen")
    except Exception as e:
        logging.error(f"Fehler beim Cleanup: {e}")
