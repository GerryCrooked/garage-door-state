import os
import sys
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, models

def retrain_model(model_path):
    print("TensorFlow Version:", tf.__version__)
    print("Keras Version:", tf.keras.__version__)

    batch_size = 32
    img_height = 224
    img_width = 224

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
        directory='/dataset',
        target_size=(img_height, img_width),
        batch_size=batch_size,
        class_mode='binary',
        subset='training'
    )

    validation_datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=0.2
    )

    validation_generator = validation_datagen.flow_from_directory(
        directory='/dataset',
        target_size=(img_height, img_width),
        batch_size=batch_size,
        class_mode='binary',
        subset='validation'
    )

    # Transfer Learning mit MobileNetV2
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

    epochs = 50  # Anzahl der Epochen auf 50 erhöht
    print("Starte Training...")
    history = model.fit(
        train_generator,
        validation_data=validation_generator,
        epochs=epochs
    )

    model.save(model_path, save_format='h5')
    print(f"Modell gespeichert unter {model_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Verwendung: python retrain.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    retrain_model(model_path)
