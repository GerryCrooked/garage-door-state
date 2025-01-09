# Garage Door State AI

This project is an AI-powered solution for monitoring and managing the state of a garage door using image classification, MQTT, and integration with Home Assistant.

---

## Features

- **Image Classification:**
  - Uses TensorFlow/Keras to classify whether the garage door is `open` or `closed` based on uploaded images.
  
- **Home Assistant Integration:**
  - Publishes the door state via MQTT with auto-discovery for seamless integration into Home Assistant.

- **Web Interface:**
  - User-friendly interface to upload images for prediction.
  - Live retraining logs displayed during model retraining.

- **Model Retraining:**
  - Ability to retrain the model directly from the web interface with dataset updates.
  - Dataset management for categorized (`open`/`closed`) images.

- **Automated Cleanup:**
  - Removes old images from the dataset and upload directories to optimize disk space.

---

## Table of Contents

1. [Installation](#installation)
2. [Environment Variables](#environment-variables)
3. [Usage](#usage)
4. [Home Assistant Setup](#home-assistant-setup)
5. [Retraining the Model](#retraining-the-model)
6. [MQTT Topics](#mqtt-topics)
7. [Contributing](#contributing)
8. [License](#license)

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GerryCrooked/garage-door-state.git
   cd garage-door-state
   ```

2. Build and start the Docker container:
   ```bash
   docker-compose up -d
   ```

3. Access the web interface at:
   ```
   http://<your-server-ip>:5000
   ```

---

## Environment Variables

Create a `.env` file in the root directory and define the following variables:

```env
# MQTT Configuration
MQTT_HOST=<your-mqtt-broker-ip>
MQTT_PORT=1883
MQTT_USER=<your-mqtt-username>
MQTT_PASSWORD=<your-mqtt-password>

# Device Configuration
TOPIC=homeassistant/binary_sensor/garage_door_status
CONFIG_TOPIC=homeassistant/binary_sensor/garage_door_status/config
STATE_TOPIC=homeassistant/binary_sensor/garage_door_status/state
SENSOR_NAME=Garage Gate Open/Close Sensor
DEVICE_ID=garage_gate_status_sensor
DEVICE_NAME=Garage Gate
DEVICE_MODEL=ARES1500
DEVICE_MANUFACTURER=BFT

# Timezone
TZ=Europe/Berlin

# Web Server Port
PORT=5000
```

---

## Usage

### Upload Images
- Use the web interface to upload images for prediction.
- The system will classify the image as `open` or `closed` and publish the result to the MQTT broker.

### View Predictions
- Visit the `/last_prediction` page to view the most recent prediction and the associated image.

### Manage Dataset
- Move images to `open` or `closed` categories via the `/action/<action>/<filename>` endpoint.
- Download or clear the dataset as needed via the web interface.

---

## Home Assistant Setup

This project supports MQTT auto-discovery, so minimal setup is required in Home Assistant. Ensure MQTT is configured correctly in Home Assistant.

The device and binary sensor will automatically appear with the following properties:

- **Device Name:** `Garage Gate`
- **Entity:** `binary_sensor.garage_gate_status`
- **State:** `open` or `closed`

### Manual Configuration (Optional)
If auto-discovery fails, add the following to your `configuration.yaml`:

```yaml
binary_sensor:
  - platform: mqtt
    name: "Garage Gate Status"
    state_topic: "homeassistant/binary_sensor/garage_door_status/state"
    payload_on: "open"
    payload_off: "closed"
    device_class: "door"
```

---

## Retraining the Model

### Automatic
- Use the `/retrain` endpoint to start retraining the model.
- Logs are displayed live on the `/last_prediction` page.

### Manual
- Add new images to the `dataset/open` and `dataset/closed` directories.
- Run the retraining script:
  ```bash
  python retrain.py /app/model/garage_door_model.keras
  ```

---

## MQTT Topics

| Topic                                      | Description                   |
|--------------------------------------------|-------------------------------|
| `homeassistant/binary_sensor/garage_door_status/config` | Auto-discovery configuration |
| `homeassistant/binary_sensor/garage_door_status/state`  | Current state of the door    |

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Submit a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
