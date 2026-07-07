# Smart Home Bridge Technical Notes

This document describes the runtime responsibilities, high-level structure,
MQTT contract, Loxone/LoxBerry integration, detector pipeline, and split
inference backend used by Smart Home Bridge.

## System Responsibilities

Smart Home Bridge is a Python backend that sits between local automation
systems and device-specific integrations.

The backend is responsible for:

- Loading runtime configuration from `.env`, process environment variables, or
  LoxBerry plugin files
- Building enabled bridge device compositions
- Connecting each enabled device runtime to MQTT
- Translating MQTT command payloads into domain commands
- Calling vendor or local integration adapters
- Calling the inference backend over HTTP when camera threat polling is enabled
- Publishing normalized state and usage events back to MQTT
- Keeping device-specific code behind adapters and controllers
- Reporting status without exposing configured secrets

The bridge is not responsible for:

- Hosting a public internet API
- Loading YOLO models or running local model inference
- Replacing the smart home controller UI
- Making autonomous door movement decisions from threat detections
- Managing Loxone function block configuration automatically

## High-Level Structure

```text
smart_home_bridge.__main__.App
   -> load_app_config()
   -> create_bridge_composition()
      -> HttpGate
      -> create_bridge_device_compositions()
         -> chicken_door composition
         -> chicken_thread_detector composition
   -> BridgeDeviceRuntime per enabled device
      -> MQTT gates and callbacks
      -> optional background services
```

Camera inference runs in a separate backend process:

```text
smart_home_inference.__main__.main
   -> load_inference_config_from_environment()
   -> uvicorn smart_home_inference.api:app
      -> ModelRegistry
      -> ChickenThreatInferenceService
      -> LocalChickenThreadDetector
```

Runtime code follows a `src` layout:

- `src/smart_home_bridge/__main__.py`: CLI entry points and application startup
- `src/smart_home_bridge/config.py`: environment and LoxBerry configuration
  loading
- `src/smart_home_bridge/composition.py`: top-level dependency composition
- `src/smart_home_bridge/runtime_status.py`: redacted status snapshots
- `src/smart_home_bridge/core/`: base device, controller, and command concepts
- `src/smart_home_bridge/bridge_devices/`: device-specific compositions,
  callbacks, controllers, and runtimes
- `src/smart_home_bridge/infrastructure/mqtt/`: Paho MQTT client wrapper and
  MQTT gate
- `src/smart_home_bridge/infrastructure/omlet/`: Omlet door adapter
- `src/smart_home_bridge/infrastructure/camera/`: ESP32-CAM HTTP client
- `src/smart_home_bridge/infrastructure/api/`: reusable HTTP client
- `src/smart_home_bridge/services/`: activity logging, `.env` updates, and MQTT
  usage reporting
- `src/smart_home_bridge/gui/`: optional PySide6 diagnostics UI
- `src/smart_home_inference/`: HTTP inference backend, model registry, and
  YOLO-backed chicken threat inference
- `src/smart_home_contracts/`: shared detection-frame contracts used by bridge
  and inference
- `deploy/loxberry/smarthomebridge/`: LoxBerry plugin payload
- `scripts/build_loxberry_plugin.py`: LoxBerry ZIP builder

## Runtime Model

Each bridge device is composed into a `BridgeDeviceComposition`. At runtime it
creates a `BridgeDeviceRuntime` containing:

- One or more `BridgeDeviceMqttBinding` objects
- A `MqttGate` per subscription
- Device-specific MQTT callbacks
- Optional background services such as the camera polling pipeline
- Handles used by tests, CLI status, and the GUI

Topics are built with `MQTT_BASE_TOPIC` plus the device topic. For example:

```text
MQTT_BASE_TOPIC=smart-home-bridge
CHICKEN_DOOR_COMMAND_TOPIC=chicken-door/command

=> smart-home-bridge/chicken-door/command
```

Incoming retained MQTT messages are ignored by bridge-device callbacks by
default. This prevents retained commands or stale detection frames from being
replayed when the backend reconnects.

## Configuration Sources

The default configuration source is `env`:

```text
SMART_HOME_BRIDGE_CONFIG_SOURCE=env
```

This uses `.env` plus process environment variables through `python-dotenv`.

For LoxBerry:

```text
SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry
```

This reads:

- LoxBerry MQTT broker settings from
  `$LBHOMEDIR/config/system/general.json`
- Bridge settings from
  `$LBPCONFIG/smarthomebridge/smart-home-bridge.ini`

LoxBerry MQTT credentials may be empty. Environment-based runtime configuration
requires `MQTT_USERNAME` and `MQTT_PASSWORD`.

Required bridge settings:

- `DOOR_API_KEY`: Omlet or SmartCoop API key
- `DOOR_DEVICE_ID`: vendor device id for the chicken door
- `MQTT_HOST`: MQTT broker host
- `MQTT_BASE_TOPIC`: MQTT namespace, for example `smart-home-bridge`

Environment mode also requires:

- `MQTT_USERNAME`
- `MQTT_PASSWORD`

Common optional settings:

- `MQTT_PORT`, default `1883`
- `MQTT_USE_TLS`, default `false`
- `HTTP_HOST`, default `0.0.0.0`
- `HTTP_PORT`, default `8080`
- `LOG_LEVEL`, default `INFO`
- `LOG_FILE_PATH`, default `logs/smart-home-bridge.log`
- `BRIDGE_DEVICES_ENABLED`, default
  `chicken_door,chicken_thread_detector`
- `CHICKEN_THREAT_ENABLED`, default `false`
- `CHICKEN_THREAT_INFERENCE_URL`, default
  `http://localhost:8090/v1/chicken-threat/infer`
- `CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS`, default `10`
- `CHICKEN_THREAT_POLL_INTERVAL_SECONDS`, default `10`

Inference backend settings:

- `INFERENCE_HTTP_HOST`, default `0.0.0.0`
- `INFERENCE_HTTP_PORT`, default `8090`
- `CHICKEN_THREAT_MODEL_PATH`, defaults to the packaged v3 model
- `CHICKEN_THREAT_CONFIDENCE_THRESHOLD`, default `0.35`
- `CHICKEN_THREAT_IMAGE_SIZE`, default `640`

## CLI Entry Points

The package exposes these console scripts:

```text
smart-home-bridge
smart-home-bridge-status
smart-home-bridge-config-check
smart-home-bridge-door-command
smart-home-inference
smart-home-bridge-gui
```

`smart-home-bridge-status` prints a JSON snapshot with configured hosts, ports,
topic bindings, runtime flags, and secret presence booleans. It does not print
API keys, MQTT passwords, or camera auth tokens.

`smart-home-bridge-door-command` publishes one validated command to the
configured chicken door command topic:

```text
open_door
close_door
stop_door
get_door_state
```

## Chicken Door

The chicken door integration is composed in
`bridge_devices/chicken_door/composition.py`.

Responsibilities:

- Subscribe to the configured door command topic
- Decode command payloads
- Validate commands through `door_controller`
- Call `OmletDoorClient` when a gateway is configured
- Map vendor door state to internal `door_status`
- Publish retained scalar state topics
- Publish non-retained command usage events

The door controller supports a local in-memory fallback model for tests, but
normal runtime composition uses `OmletDoorClient`.

`OmletDoorClient` maps vendor state into:

- `position`
- `fault`
- `light_level`
- `battery_level`
- `power_source`
- `wifi_strength`
- `connected`
- `last_open_time`
- `last_close_time`

If an action succeeds but the state refresh fails, the adapter falls back to the
vendor action's pending state when available.

## Chicken Door MQTT Contract

Default command topic:

```text
smart-home-bridge/chicken-door/command
```

Supported command payloads:

```text
open_door
close_door
stop_door
get_door_state
```

Default retained status topics:

```text
smart-home-bridge/chicken-door/status
smart-home-bridge/chicken-door/status_code
smart-home-bridge/chicken-door/fault
smart-home-bridge/chicken-door/connected
smart-home-bridge/chicken-door/battery
smart-home-bridge/chicken-door/light_level
```

`status` values:

```text
open
closed
opening
closing
openpending
closepending
stopping
unknown
```

`status_code` values:

```text
0 = unknown
1 = open
2 = closed
3 = opening or openpending
4 = closing or closepending
5 = stopping
6 = fault
```

Default diagnostic values are published when vendor data is missing:

- `fault`: `none`
- `connected`: `1`
- `battery`: `100`
- `light_level`: `0`

## Chicken Threat Detector

The detector device is named `chicken_thread_detector` in code and uses the
default MQTT topic `chicken-thread-detector`. The domain behavior is threat
assessment.

It supports two input modes:

1. MQTT detection injection: publish a JSON detection frame to the detector
   topic.
2. Camera polling pipeline: enable `CHICKEN_THREAT_ENABLED=true` so the backend
   periodically fetches an ESP32-CAM JPEG and sends it to the HTTP inference
   backend.

The detector pipeline is independent from the door controller. It publishes
assessments but does not open, close, stop, or inspect the chicken door.

Default detector topic:

```text
smart-home-bridge/chicken-thread-detector
```

Manual or external detection input:

```json
{
  "source": "coop-camera",
  "detections": [
    {
      "label": "dog",
      "confidence": 0.9,
      "box": null
    }
  ]
}
```

Published assessment:

```json
{
  "level": "medium",
  "score": 0.675,
  "detection_count": 1,
  "triggering_detections": [
    {
      "label": "dog",
      "confidence": 0.9,
      "box": null
    }
  ]
}
```

Detector commands on the same topic:

```text
get_detector_state
reset_detector_state
```

Published assessment payloads are ignored as inputs because they do not contain
a `detections` array.

## Threat Scoring

Bridge-side threat scoring uses:

- Confidence threshold: `0.35`
- Medium threshold: `0.4`
- High threshold: `0.7`
- Critical threshold: `0.9`

Risk weights:

```text
chicken = 0.0
other_poultry = 0.0
person = 0.0
cat = 0.55
dog = 0.75
wild_mammal_threat = 0.95
rodent = 0.65
bird = 0.6
```

Aliases:

```text
fox -> wild_mammal_threat
marten -> wild_mammal_threat
weasel -> wild_mammal_threat
marten_weasel -> wild_mammal_threat
other_bird -> bird
bird_of_prey -> bird
```

The final score is the maximum `risk_weight * confidence` among detections above
the confidence threshold. `detection_count` counts all detections above the
confidence threshold, including non-threatening labels.

## Camera Pipeline

When `CHICKEN_THREAT_ENABLED=true`, the detector runtime creates a
`ChickenThreatDetectionPipeline`.

Pipeline flow:

```text
ESP32-CAM /jpg
   -> CameraClient.fetch_jpeg()
   -> ChickenThreatInferenceClient.detect()
   -> HTTP POST image/jpeg to CHICKEN_THREAT_INFERENCE_URL
   -> smart_home_inference API
   -> ChickenThreatInferenceService
   -> LocalChickenThreadDetector / YOLO
   -> DetectionFrame JSON
   -> DangerScorer
   -> detector MQTT assessment publish
   -> usage/camera-inference event
```

Startup behavior:

- The pipeline calls the configured camera health endpoint before polling.
- If health check fails, the pipeline is not started.
- Each poll fetches JPEG bytes, posts them to the inference backend, scores the
  returned detections, and publishes the assessment.
- Poll failures are printed and the loop continues after the configured
  interval.
- The inference backend validates JPEG content, decodes with Pillow, checks
  image limits, runs YOLO inference, and returns raw detections.

Camera settings:

- `CAMERA_HOST`, default `192.168.1.42`
- `CAMERA_PORT`, default `80`
- `CAMERA_JPG_ENDPOINT`, default `/jpg`
- `CAMERA_HEALTH_ENDPOINT`, default `/health`
- `CAMERA_TIMEOUT_SECONDS`, default `5`
- `CAMERA_MAX_JPEG_BYTES`, default `2000000`
- `CAMERA_AUTH_TOKEN`, optional bearer token

Threat settings:

- `CHICKEN_THREAT_ENABLED`, default `false`
- `CHICKEN_THREAT_INFERENCE_URL`, default
  `http://localhost:8090/v1/chicken-threat/infer`
- `CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS`, default `10`
- `CHICKEN_THREAT_POLL_INTERVAL_SECONDS`, default `10`

Inference backend settings:

- `INFERENCE_HTTP_HOST`, default `0.0.0.0`
- `INFERENCE_HTTP_PORT`, default `8090`
- `CHICKEN_THREAT_MODEL_PATH`, defaults to the packaged v3 model
- `CHICKEN_THREAT_CONFIDENCE_THRESHOLD`, default `0.35`
- `CHICKEN_THREAT_IMAGE_SIZE`, default `640`

Inference endpoints:

```text
GET /health
GET /ready
GET /v1/models
POST /v1/chicken-threat/infer
POST /v1/models/chicken-threat/infer
```

Inference requests must use `Content-Type: image/jpeg`. Successful responses
are shared `DetectionFrame` JSON payloads.

## MQTT Usage Events

Usage events are JSON and non-retained.

Door command usage topic:

```text
smart-home-bridge/usage/chicken-door
```

Payload shape:

```json
{
  "event": "chicken_door_command",
  "command": "open_door",
  "success": true,
  "position": "open",
  "timestamp": "2026-07-05T12:00:00+00:00"
}
```

Camera inference usage topic:

```text
smart-home-bridge/usage/camera-inference
```

Payload shape:

```json
{
  "event": "camera_inference",
  "source": "esp32cam.local",
  "success": true,
  "level": "medium",
  "score": 0.675,
  "detection_count": 1,
  "timestamp": "2026-07-05T12:00:00+00:00"
}
```

## Loxone and LoxBerry

Smart Home Bridge is intended to sit beside Loxone rather than inside the
Miniserver.

Typical control path:

```text
Loxone App
   -> Loxone function block or virtual output
   -> LoxBerry MQTT Gateway
   -> MQTT command topic
   -> Smart Home Bridge backend
   -> Omlet vendor API
   -> Smart Home Bridge retained state topics
   -> LoxBerry MQTT Gateway
   -> Loxone virtual inputs
   -> Loxone UI status
```

Recommended Loxone mapping:

- Use a Garage/Gate or similar block for the chicken door command surface.
- Publish `open_door`, `close_door`, `stop_door`, or `get_door_state` to the
  command topic.
- Map `status_code` to a numeric virtual input for simple logic.
- Map `status`, `fault`, `connected`, `battery`, and `light_level` to diagnostic
  virtual inputs where useful.
- Keep broker, bridge, and camera endpoints on the same trusted LAN.

The LoxBerry plugin payload provides:

- `plugin.cfg` at the archive root
- lifecycle hooks for install, upgrade, and uninstall
- `bin/bridge_ctl.sh` for service commands
- `config/smart-home-bridge.ini` for bridge settings
- `webfrontend/htmlauth/index.php` for status, start/stop/restart,
  bridge and inference service controls, configuration editing, log tail, and
  manual door command publishing
- MQTT Gateway seed files for subscriptions, conversions, and reset-after-send
- Python package payload for bridge runtime and inference source files. Heavy
  inference dependencies are not installed automatically on LoxBerry.

Build the plugin archive with:

```bash
python scripts/build_loxberry_plugin.py
```

Upload:

```text
build/smarthomebridge-loxberry.zip
```

The ZIP must contain `plugin.cfg` directly at the root.

## LoxBerry Bridge Control

`bridge_ctl.sh` supports:

```text
start
stop
restart
start-bridge
stop-bridge
start-inference
stop-inference
install-inference
status
dump-config
door-command open_door
door-command close_door
door-command stop_door
door-command get_door_state
```

`start` starts the bridge runtime only. `stop` stops the bridge first and then
inference if it is running.

The script exports `SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry`, resolves
standard LoxBerry directories from `LBPBIN`, `LBPCONFIG`, `LBHOMEDIR`,
`LBPDATA`, and `LBPLOG`, and writes process output to the plugin log directory.
The plugin installs the bridge virtual environment at
`$LBPDATA/smarthomebridge/venv`. The inference extra is intentionally skipped
because Torch and Ultralytics can require multiple GB of disk space; run the
inference service with Docker or install `.[inference]` manually on a larger
host when local model serving is required.

## Docker Runtime

The bridge Docker image uses `python:3.12-slim`, installs the package without
optional extras, and runs:

```text
smart-home-bridge
```

The inference Docker image uses `Dockerfile.inference`, installs the package
with the `inference` extra, and runs:

```text
smart-home-inference
```

Compose runs only the bridge by default:

```bash
docker compose up -d
```

Run inference as well with:

```bash
docker compose --profile inference up -d
```

Run only the inference backend with:

```bash
docker compose --profile inference up -d smart-home-inference
```

Neither image installs `.[gui]`, so PySide6 is not present in container runtime.
Use the local `smart-home-bridge-gui` entry point for desktop diagnostics.

## Desktop GUI

The GUI is optional and local-only. It shows:

- MQTT and backend status
- Current door state and command topic
- HTTP diagnostics endpoint
- Chicken threat detector topic, camera endpoint, risk level, score, and
  detection count
- Manual door controls
- One-off camera inference through the HTTP inference backend with annotated
  detections
- Activity output written to `LOG_FILE_PATH`
- Environment settings for selected MQTT and HTTP values

The GUI can save selected settings to `.env`; runtime processes must be
restarted to pick up changed configuration.

## Security Notes

- Do not expose MQTT, camera, or bridge HTTP endpoints directly to the internet.
- Store API keys, MQTT credentials, camera tokens, and firmware secrets outside
  source control.
- Use MQTT authentication and ACLs for command topics.
- Treat door movement as safety-sensitive. Retained MQTT commands are ignored by
  callbacks, but command topics should still be write-restricted.
- Status snapshots intentionally report whether secrets are configured without
  printing the secret values.
