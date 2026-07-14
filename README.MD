# Smart Home Bridge

Smart Home Bridge connects LAN smart home systems to devices that are awkward to
integrate directly. It normalizes device commands and state through MQTT so a
controller such as Loxone can use stable topics instead of calling vendor APIs,
camera endpoints, or inference APIs itself.

The current bridge supports:

- Omlet chicken door control through `smartcoop-python-sdk`
- Retained MQTT door status topics for state, numeric status, fault, connection,
  battery, and light level
- Chicken threat assessment from either injected MQTT detection payloads or an
  optional ESP32-CAM polling pipeline
- Split inference backend with YOLO-based chicken threat detection and one
  Git-LFS-managed, manifest-verified production model
- Optional PySide6 desktop diagnostics and manual controls
- Docker runtimes for the bridge service and optional inference service
- Modular LoxBerry plugin packaging, settings, service control, log tail, and
  device-specific controls


Supported LoxBerry Plugins:

- OmletChickenDoorPlugin
- ChickenBarnCameraPlugin


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
pip install -e ".[ml]"        # dataset/training/promotion workflow
```

3. Run the backend:

```bash
smart-home-bridge
```

4. Run the optional inference backend when camera threat polling is enabled:

```bash
smart-home-inference
```

The inference backend requires the `inference` extra.

## Chicken-Threat ML Workflow

The training lifecycle is deliberately separate from deployment. A local,
gitignored ML workspace prepares and inspects a source-metadata-driven dataset,
Kaggle trains a candidate, and a human promotes a candidate only after the
fixed v4 test and barn holdout gates pass. The release contains only the
approved production model in the inference package/image; LoxBerry continues to
use the external inference service.

Install the locked environment with `uv sync --extra ml --locked`, then see
[the ML workflow guide](ml/chicken_threat/README.md). Candidate weights,
datasets, and source images must not be committed.

5. Run the optional desktop GUI:

```bash
smart-home-bridge-gui
```

6. Check configuration or publish a manual door command:

```bash
smart-home-bridge-config-check
smart-home-bridge-status
smart-home-bridge-door-command open_door
```

Supported door commands are `open_door`, `close_door`, `stop_door`, and
`get_door_state`.

7. Run tests:

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
`HTTP_PORT`, `OMLET_WEBHOOK_ENABLED`, `OMLET_WEBHOOK_TOKEN`, `LOG_LEVEL`,
`LOG_FILE_PATH`, `BRIDGE_DEVICES_ENABLED`,
`CAMERA_HOST`, `CAMERA_PORT`, `CHICKEN_THREAT_ENABLED`,
`CHICKEN_THREAT_INFERENCE_URL`, and
`CHICKEN_THREAT_POLL_INTERVAL_SECONDS`.

Set `MQTT_BASE_TOPIC` to the namespace only, for example
`smart-home-bridge`. Device topics are appended by the bridge.

## Omlet Door-State Webhooks

Enable the private receiver and set a unique random token containing at least
32 characters:

```dotenv
HTTP_HOST=0.0.0.0
HTTP_PORT=8080
OMLET_WEBHOOK_ENABLED=true
OMLET_WEBHOOK_TOKEN=replace-with-a-unique-random-secret
```

The receiver provides:

```text
GET  /health
POST /webhooks/omlet/door-state
```

Do not expose port 8080 directly to the internet. Omlet sends the configured
token with each request, so the public leg must use HTTPS to prevent credential
disclosure. Terminate TLS at a reverse proxy with a publicly trusted
certificate or at a named managed tunnel, and forward only the webhook path to
`http://<bridge-private-address>:8080`.

For Caddy or an equivalent reverse proxy, configure DNS or DDNS for the public
hostname, permit inbound TCP 443, and use a path-limited route such as:

```caddyfile
hooks.example.com {
    @omlet path /webhooks/omlet/door-state
    reverse_proxy @omlet 192.168.1.50:8080
}
```

Alternatively, configure a durable named tunnel whose public hostname routes
to `http://192.168.1.50:8080`. Do not place an interactive access-login policy
in front of the route because Omlet cannot complete it. In either arrangement,
do not expose the LoxBerry administration interface.

In the Omlet developer console, create a webhook with the public URL
`https://hooks.example.com/webhooks/omlet/door-state`, select only **Door
State**, and enter the same token as `OMLET_WEBHOOK_TOKEN`. Confirm that the
registration test succeeds, then verify a real transition in Omlet's webhook
event history and on the retained MQTT state topics. Keep this token separate
from `DOOR_API_KEY`.

For a local receiver check:

```bash
curl http://127.0.0.1:8080/health
curl -X POST http://127.0.0.1:8080/webhooks/omlet/door-state \
  -H "Authorization: Bearer $OMLET_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"deviceId":"your-device-id","parameterName":"Door State","oldValue":"closed","newValue":"open"}'
```

## Docker

Run the bridge with Docker Compose:

```bash
docker compose up -d
```

Run the bridge plus inference backend:

```bash
docker compose --profile inference up -d
```

Run only the inference backend:

```bash
docker compose --profile inference up -d smart-home-inference
```

Build the bridge image directly:

```bash
docker build -t smart-home-bridge:local .
```

Build the inference image directly:

```bash
docker build -f Dockerfile.inference -t smart-home-inference:local .
```

The bridge image installs only bridge runtime dependencies and runs
`smart-home-bridge`. The inference image installs `.[inference]` and runs
`smart-home-inference`. Neither image installs the optional PySide6 GUI
dependencies.

## Modular LoxBerry Plugins

List the available device plugins:

```bash
python scripts/build_loxberry_plugin.py --list
```

Build both plugins, or select one by its stable manifest id:

```bash
python scripts/build_loxberry_plugin.py
python scripts/build_loxberry_plugin.py --plugin omlet-chicken-door
python scripts/build_loxberry_plugin.py --plugin chicken-barn-camera
```

The builds are written to `build/loxberry/omlet-chicken-door-loxberry.zip` and
`build/loxberry/chicken-barn-camera-loxberry.zip`. Upload only the plugin needed
for that device, or install both independently. Do not upload a GitHub source
archive or a ZIP of the repository root; LoxBerry expects `plugin.cfg` directly
at the archive root.

`OmletChickenDoorPlugin` contains door credentials, an authenticated private
webhook listener, door topics, retained door state subscriptions, and manual
door commands. `ChickenBarnCameraPlugin`
contains camera, detector, and external inference settings without requiring
Omlet credentials.

When `SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry`, the bridge reads MQTT broker
settings from LoxBerry's system MQTT configuration and bridge-specific settings
from `smart-home-bridge.ini`.

Each plugin installs the same shared bridge runtime during LoxBerry installation
and fixes `BRIDGE_DEVICES_ENABLED` to its own domain. Shared payload files live
under `deploy/loxberry/shared`; device profiles and machine-readable manifests
live under `deploy/loxberry/plugins`. The manifest catalog is intended to be the
input for a later interactive ZIP or Docker-image installer.

Inference dependencies such as Torch and Ultralytics can require multiple GB of
disk space, so run inference with Docker or install `.[inference]` manually on a
larger host. The LoxBerry web UI exposes the bridge lifecycle, config checks,
log tailing, and settings; manual door commands appear only in the door plugin.

## GUI

The GUI is for local diagnostics and manual operation. It can show bridge
status, MQTT topics, current door state, activity logs, camera/detector status,
one-off threat inference results from the HTTP inference backend, and annotated
camera frames. It can also write selected MQTT and HTTP settings back to `.env`.

## Safety

- Keep MQTT, camera, and configured HTTP endpoints on a trusted LAN.
- Use MQTT authentication and restrict ACLs where possible.
- Never commit `.env`, firmware `secrets.h`, API keys, MQTT passwords, camera
  tokens, broker details, or private model data.
- Treat door movement as safety-sensitive: validate command topics and payloads,
  publish confirmed state, and preserve manual override behavior.

## License

MIT
