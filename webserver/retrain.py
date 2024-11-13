import os
import sys
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import load_model
from tensorflow.keras import layers, models
import numpy as np

def retrain_model(open_dir, closed_dir, model_path):
    # Parameter überprüfen
    if not os.path.exists(open_dir) or not os.path.exists(closed_dir):
        print("Die angegebenen Dataset-Ordner existieren nicht.")
        sys.exit(1)
    
    # Bilddaten vorbereiten
    batch_size = 32
    img_height = 180
    img_width = 180

    # Daten-Generatoren für Training und Validierung
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=0.2
    )

    train_generator = train_datagen.flow_from_directory(
        directory=os.path.dirname(open_dir),
        target_size=(img_height, img_width),
        batch_size=batch_size,
        class_mode='binary',
        subset='training'
    )

    validation_generator = train_datagen.flow_from_directory(
        directory=os.path.dirname(open_dir),
        target_size=(img_height, img_width),
        batch_size=batch_size,
        class_mode='binary',
        subset='validation'
    )

    # Modell laden oder neues Modell erstellen
    if os.path.exists(model_path):
        print("Lade vorhandenes Modell...")
        model = load_model(model_path)
    else:
        print("Erstelle neues Modell...")
        num_classes = 1  # Binary Classification
        model = models.Sequential([
            layers.InputLayer(input_shape=(img_height, img_width, 3)),
            layers.Conv2D(16, 3, padding='same', activation='relu'),
            layers.MaxPooling2D(),
            layers.Conv2D(32, 3, padding='same', activation='relu'),
            layers.MaxPooling2D(),
            layers.Conv2D(64, 3, padding='same', activation='relu'),
            layers.MaxPooling2D(),
            layers.Flatten(),
            layers.Dense(128, activation='relu'),
            layers.Dense(num_classes, activation='sigmoid')
        ])
        model.compile(optimizer='adam',
                      loss='binary_crossentropy',
                      metrics=['accuracy'])

    # Modell trainieren
    epochs = 5
    print("Starte Training...")
    history = model.fit(
        train_generator,
        validation_data=validation_generator,
        epochs=epochs
    )

    # Modell speichern
    model.save(model_path)
    print(f"Modell gespeichert unter {model_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Verwendung: python retrain.py <open_dir> <closed_dir> <model_path>")
        sys.exit(1)

    open_dir = sys.argv[1]
    closed_dir = sys.argv[2]
    model_path = sys.argv[3]

    retrain_model(open_dir, closed_dir, model_path)
