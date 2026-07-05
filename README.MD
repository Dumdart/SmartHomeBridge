# Smart Home Bridge

Smart Home Bridge connects LAN smart home systems to devices that are awkward to
integrate directly. It normalizes device commands and state through MQTT so a
controller such as Loxone can use stable topics instead of calling vendor APIs,
camera endpoints, or local inference code itself.

The current bridge supports:

- Omlet chicken door control through `smartcoop-python-sdk`
- Retained MQTT door status topics for state, numeric status, fault, connection,
  battery, and light level
- Chicken threat assessment from either injected MQTT detection payloads or an
  optional ESP32-CAM polling pipeline
- Local YOLO-based camera inference with the packaged
  `chicken_threat_detector_best_v3.pt` model
- Optional PySide6 desktop diagnostics and manual controls
- Docker runtime for the backend service
- LoxBerry plugin packaging, settings, service control, log tail, and manual
  door command publishing

For deeper architecture, MQTT, Loxone, and configuration details, see
[TECHNICAL.MD](TECHNICAL.MD).

## Development

1. Copy `.env.example` to `.env` and set the required door and MQTT values.
   Configure camera and detector values when you use threat inference.

2. Install the package from the repository root:

```bash
pip install -e ".[dev]"
```

Install optional extras when needed:

```bash
pip install -e ".[gui]"
pip install -e ".[inference]"
```

3. Run the backend:

```bash
smart-home-bridge
```

4. Run the optional desktop GUI:

```bash
smart-home-bridge-gui
```

5. Check configuration or publish a manual door command:

```bash
smart-home-bridge-config-check
smart-home-bridge-status
smart-home-bridge-door-command open_door
```

Supported door commands are `open_door`, `close_door`, `stop_door`, and
`get_door_state`.

6. Run tests:

```bash
pytest
```

## Runtime Configuration

The default configuration source is `.env` or process environment variables.
Required values are:

- `DOOR_API_KEY`
- `DOOR_DEVICE_ID`
- `MQTT_HOST`
- `MQTT_USERNAME`
- `MQTT_PASSWORD`
- `MQTT_BASE_TOPIC`

Common optional values include `MQTT_PORT`, `MQTT_USE_TLS`, `HTTP_HOST`,
`HTTP_PORT`, `LOG_LEVEL`, `LOG_FILE_PATH`, `BRIDGE_DEVICES_ENABLED`,
`CAMERA_HOST`, `CAMERA_PORT`, and `CHICKEN_THREAT_ENABLED`.

Set `MQTT_BASE_TOPIC` to the namespace only, for example
`smart-home-bridge`. Device topics are appended by the bridge.

## Docker

Run the backend with Docker Compose:

```bash
docker compose up -d
```

Build the image directly:

```bash
docker build -t smart-home-bridge:local .
```

Docker runs only the backend service. The image installs inference dependencies
but not the optional PySide6 GUI dependencies, and the container command is
`smart-home-bridge`.

## LoxBerry Plugin

Build the LoxBerry plugin ZIP from the plugin payload directory:

```bash
python scripts/build_loxberry_plugin.py
```

Upload `build/smarthomebridge-loxberry.zip` to LoxBerry. Do not upload a GitHub
source archive or a ZIP of the repository root; LoxBerry expects `plugin.cfg`
directly at the archive root.

When `SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry`, the bridge reads MQTT broker
settings from LoxBerry's system MQTT configuration and bridge-specific settings
from `smart-home-bridge.ini`.

## GUI

The GUI is for local diagnostics and manual operation. It can show bridge
status, MQTT topics, current door state, activity logs, camera/detector status,
one-off threat inference results, and annotated camera frames. It can also write
selected MQTT and HTTP settings back to `.env`.

## Safety

- Keep MQTT, camera, and configured HTTP endpoints on a trusted LAN.
- Use MQTT authentication and restrict ACLs where possible.
- Never commit `.env`, firmware `secrets.h`, API keys, MQTT passwords, camera
  tokens, broker details, or private model data.
- Treat door movement as safety-sensitive: validate command topics and payloads,
  publish confirmed state, and preserve manual override behavior.

## License

MIT
