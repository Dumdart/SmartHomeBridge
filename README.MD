# Smart Home Bridge

Smart Home Bridge helps connect local smart home systems with devices that do not expose a clean or compatible integration interface. Many smart home platforms provide customizable apps and controls, while individual devices often rely on vendor-specific APIs that are difficult to integrate directly.

This project provides a configurable bridge between those devices and MQTT. Smart home systems can then read state and send commands through MQTT topics instead of talking to each vendor API directly.

Smart Home Bridge can run from the console, from the optional local desktop GUI, or inside Docker. Custom devices can be defined and wired into the same bridge pattern.

## Architecture on Loxone

```text
Loxone App
   ->
Loxone Virtual Output
   -> UDP/HTTP command to LoxBerry MQTT Gateway
   ->
MQTT topic: barn/chicken-door/cmd
   ->
Python backend/plugin
   ->
Door vendor API
   ->
Python backend publishes state
   ->
MQTT topic: barn/chicken-door/state/*
   ->
LoxBerry MQTT Gateway
   -> HTTP/UDP to Loxone Virtual Inputs
   ->
Loxone UI status
```

The Loxone App is not integrated directly with the device vendor API. Instead, the backend communicates through MQTT, and the Loxone Miniserver exposes controls and status through configured function blocks such as Garage/Gate or Door/Window Monitor.

## Responsibilities

### Python Backend

* Authenticate against the door vendor API
* Translate MQTT commands into API calls
* Poll or receive door state
* Publish normalized state to MQTT
* Expose optional HTTP diagnostics
* Handle retries, timeouts, and error states
* Keep vendor-specific logic isolated behind adapters

### Local Desktop GUI

The optional PySide6 GUI is intended for local startup and diagnostics only. It
is available through the `smart-home-bridge-gui` console script after installing the
`gui` extra, and is not installed or started by the Docker image.

The GUI provides:

* Bridge status, including current door state, command MQTT topic, and HTTP diagnostics endpoint
* Chicken threat detector status, MQTT topic, camera endpoint, risk level, score, and detection count
* Manual threat inference that fetches the configured ESP32-CAM JPEG and renders detected objects with labeled borders
* Environment Settings for MQTT host, port, username, password, base topic, HTTP host, and HTTP port
* Save Environment support that writes MQTT and HTTP updates to `.env`
* Chicken door controls for open, close, stop, and refresh
* Activity logging in the window and in `LOG_FILE_PATH`, defaulting to `logs/loxone-bridge.log`

### MQTT Broker

* Provide the local message bus between the backend and Loxone
* Recommended: Mosquitto
* Run on the same LAN as the Miniserver
* Use authentication and restricted ACLs

### Chicken Threat Detector

The chicken threat detector can run as an independent backend pipeline:

```text
ESP32-CAM /jpg
   -> backend camera client fetches JPEG bytes
   -> local YOLO inference with chicken_threat_detector_best.pt
   -> danger scoring
   -> MQTT detector assessment publish
```

This pipeline is separate from the chicken door controller. It does not call
door commands, inspect door state, or reuse the door HTTP API configuration.
The existing detector MQTT payload path remains available for manual or test
injection of precomputed detections.

Configure the detector with:

* `CAMERA_HOST`: ESP32-CAM host or IP address
* `CAMERA_PORT`: ESP32-CAM HTTP port, usually `80`
* `CAMERA_JPG_ENDPOINT`: JPEG endpoint, usually `/jpg`
* `CAMERA_HEALTH_ENDPOINT`: optional health endpoint, usually `/health`
* `CAMERA_TIMEOUT_SECONDS`: camera request timeout
* `CHICKEN_THREAT_ENABLED`: set to `true` to start backend polling
* `CHICKEN_THREAT_MODEL_PATH`: local YOLO model path
* `CHICKEN_THREAT_POLL_INTERVAL_SECONDS`: seconds between camera frames

Detector assessments are published on the detector MQTT topic, for example
`barn/chicken-door/chicken-thread-detector`, as JSON:

```json
{"level":"medium","score":0.675,"detection_count":1,"triggering_detections":[{"label":"dog","confidence":0.9,"box":null}]}
```

## Development

1. Configure environment variables in `.env` or set them directly in the shell. See `.env.example` for the available settings.

2. Install dependencies:

```bash
pip install -e ".[dev]"
```

Install the optional desktop GUI dependencies when you want the local control
panel. The GUI is a local development/runtime tool and is not part of the
Docker image:

```bash
pip install -e ".[gui]"
```

For backend-only local threat inference without the desktop GUI, install:

```bash
pip install -e ".[inference]"
```

3. Run the backend from the repository root:

```bash
python .\src\smart_home_bridge\__main__.py
```

Run the PySide6 GUI locally:

```bash
smart-home-bridge-gui
```

Use the GUI to inspect bridge status, trigger chicken door commands, review
activity output, run one-off chicken threat inference, review the annotated
camera frame, and edit MQTT/HTTP environment settings. Save Environment writes
those values to `.env`; restart any already-running backend service for that
process to pick up the changed environment.

4. Run tests:

```bash
pytest
```

5. Run with Docker Compose:

```bash
docker compose up -d
```

Docker runs only the bridge service logic. The Dockerfile installs the base
package without the optional PySide6 GUI dependencies, and the container command
is `loxone-bridge`. Start the GUI locally with `smart-home-bridge-gui` when you need
desktop controls or diagnostics.

Build the image directly:

```bash
docker build -t loxone-bridge:local .
```

The compose service reads runtime settings from `.env`. Set `MQTT_HOST`,
`MQTT_PORT`, `MQTT_USERNAME`, and `MQTT_PASSWORD` to the broker that the
smart home system can reach.

The desktop GUI writes the same activity messages shown in the Activity panel
to `LOG_FILE_PATH`. If the variable is not set, logs are appended to
`logs/loxone-bridge.log`.

## Safety Requirements

* Do not expose MQTT or backend HTTP directly to the internet
* Use MQTT authentication
* Store API credentials outside source code
* Implement command timeout handling
* Publish `unknown` state if the vendor API is unreachable
* Keep manual override possible
* Avoid automatic close unless safety/obstruction handling is verified
* Log all commands and resulting state transitions

## License

MIT - free to use!
