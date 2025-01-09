import os
import sys
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, models
from datetime import datetime, timedelta

# Pfade
LOCK_FILE = '/app/retrain.lock'
LOG_FILE = '/app/retrain.log'

def setup_logging():
    """Bereitet die Logdatei vor."""
    if not os.path.exists(LOCK_FILE):
        # Logdatei löschen, wenn kein Lockfile existiert
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        with open(LOG_FILE, 'w') as log_file:
            log_file.write("Starte neues Retraining...\n")

def append_log(message):
    with open('/app/retrain.log', 'a') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def lock():
    """Setzt einen Lock, um paralleles Retraining zu verhindern."""
    with open(LOCK_FILE, 'w') as lock_file:
        lock_file.write("locked")
    append_log(f"Lock-Datei erstellt: {LOCK_FILE}")

def unlock():
    """Entfernt den Lock, wenn das Retraining abgeschlossen ist."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
        append_log(f"Lock-Datei entfernt: {LOCK_FILE}")

def is_locked():
    """Überprüft, ob ein Retraining-Lock existiert."""
    return os.path.exists(LOCK_FILE)

def retrain_model(model_path):
    setup_logging()

    if is_locked():
        append_log("Retraining läuft bereits. Abbruch.")
        print("Retraining läuft bereits. Abbruch.")
        return

    try:
        lock()
        append_log("TensorFlow Version: " + tf.__version__)
        append_log("Keras Version: " + tf.keras.__version__)
        # Startzeit speichern
        start_time = datetime.now()
        append_log(f"Startzeit: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        batch_size = 32
        img_height = 512
        img_width = 896

        # Daten-Generatoren mit Datenaugmentation
        train_datagen = ImageDataGenerator(
            rescale=1./255,
            validation_split=0.2,
            rotation_range=40,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True,
            fill_mode='nearest'
        )

        train_generator = train_datagen.flow_from_directory(
            directory='/app/dataset',
            target_size=(img_height, img_width),
            batch_size=batch_size,
            class_mode='binary',
            subset='training'
        )
        append_log(f"Training Images: {train_generator.samples} found.")

        validation_datagen = ImageDataGenerator(
            rescale=1./255,
            validation_split=0.2
        )

        validation_generator = validation_datagen.flow_from_directory(
            directory='/app/dataset',
            target_size=(img_height, img_width),
            batch_size=batch_size,
            class_mode='binary',
            subset='validation'
        )
        append_log(f"Validation Images: {validation_generator.samples} found.")

        # Modell erstellen oder bestehendes Modell laden
        if os.path.exists(model_path):
            append_log(f"Lade bestehendes Modell: {model_path}")
            model = tf.keras.models.load_model(model_path)
        else:
            append_log("Erstelle neues Modell...")
            base_model = tf.keras.applications.MobileNetV2(
                input_shape=(img_height, img_width, 3),
                include_top=False,
                weights='imagenet'
            )
            base_model.trainable = False  # Basismodell einfrieren

            model = models.Sequential([
                base_model,
                layers.GlobalAveragePooling2D(),
                layers.Dense(1, activation='sigmoid')
            ])

            model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
                loss='binary_crossentropy',
                metrics=['accuracy']
            )
            append_log(f"Neues Modell erfolgreich erstellt.")

        # Feinjustierung aktivieren
        if 'base_model' in locals():
            append_log("Feinjustierung der letzten Schichten...")
            base_model.trainable = True
            fine_tune_at = len(base_model.layers) - 5  # Letzte 5 Schichten feinjustieren
            for layer in base_model.layers[:fine_tune_at]:
                layer.trainable = False

            model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=0.00001),
                loss='binary_crossentropy',
                metrics=['accuracy']
            )

        epochs = 25  # Reduzierte Anzahl an Epochen
        append_log("Starte Training...")
        history = model.fit(
            train_generator,
            validation_data=validation_generator,
            epochs=epochs,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor='val_loss',  # Überwacht Validierungsverlust
                    patience=5,  # Stoppt, wenn sich Val_Loss für 5 Epochen nicht verbessert
                    restore_best_weights=True
                ),
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=3,
                    min_lr=1e-6,
                    verbose=1
                ),
                tf.keras.callbacks.LambdaCallback(on_epoch_end=lambda epoch, logs: append_log(
                    f"Epoche {epoch+1}/{epochs}: Loss: {logs['loss']:.4f}, Accuracy: {logs['accuracy']:.4f}, "
                    f"Val_Loss: {logs['val_loss']:.4f}, Val_Accuracy: {logs['val_accuracy']:.4f}"
                ))
            ]
        )

        model.save(model_path, save_format='keras')
        append_log(f"Modell gespeichert unter {model_path}")

        # Endzeit und Dauer berechnen
        end_time = datetime.now()
        duration = end_time - start_time
        append_log(f"Endzeit: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        append_log(f"Dauer des Trainings: {str(timedelta(seconds=duration.total_seconds()))}")

    except Exception as e:
        append_log(f"Fehler während des Retrainings: {e}")
        print(f"Fehler während des Retrainings: {e}")
    finally:
        unlock()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Verwendung: python retrain.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    retrain_model(model_path)
