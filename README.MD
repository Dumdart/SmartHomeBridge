# Smart Home Bridge

Connect an Omlet Smart Automatic Chicken Coop Door to MQTT and Loxone without
exposing vendor APIs directly to your home-automation controller.

Smart Home Bridge polls the door through `smartcoop-python-sdk`, translates its
state and telemetry into stable, retained MQTT topics, and accepts door commands
over MQTT. It can run as a Python service, in Docker, or as a LoxBerry plugin.

> [!IMPORTANT]
> This is a personal project built for a specific smart-home setup. Review the
> configuration, MQTT topics, and safety guidance before using it with physical
> equipment.

## What it does

- Controls an Omlet chicken door through MQTT.
- Polls and publishes the door position, numeric status, fault state,
  connectivity, battery level, and light level.
- Retains the latest door state so controllers receive it immediately after
  subscribing.
- Runs without webhooks, public ports, DNS, or TLS certificates for the Omlet
  integration.
- Provides health, configuration-check, runtime-status, and manual-command
  tooling.
- Packages the integration as a dedicated LoxBerry plugin.
- Optionally runs an ESP32-CAM and YOLO inference experiment for chicken-threat
  detection.

For MQTT contracts, architecture, configuration sources, and Loxone integration
details, see [TECHNICAL.MD](TECHNICAL.MD).

## Project status

The Omlet door integration is the main purpose of this repository.

The `ChickenBarnCameraPlugin`, inference service, ESP32-CAM firmware, and model
training workflow are an experiment. The pipeline works end to end and can run
inference, but the current model is not good enough to rely on for accurate
threat detection. I later concluded that this experiment should have lived in
an independent repository; keeping it here makes the project harder to read and
obscures the otherwise focused door bridge. It remains included because it is
functional and documents the experiment, not because it should be treated as a
production-ready safety system.

## How it fits together

```text
Omlet door API
      |
      v
Smart Home Bridge <----> MQTT broker <----> Loxone / other MQTT clients

ESP32-CAM  --->  Smart Home Bridge  --->  Inference service (experimental)
```

The bridge is deliberately headless. Use an MQTT client such as
SmartHomeObserver for monitoring and diagnostics. The LoxBerry pages are
deployment adapters for configuration, service control, logs, and manual door
commands.

## Requirements

- Python 3.11 or newer, or Docker with Docker Compose
- An MQTT broker
- An Omlet API key and device ID for the door integration
- A trusted local network
- LoxBerry only when using the packaged LoxBerry plugin

The optional inference service has much heavier dependencies, including Torch
and Ultralytics, and can require several gigabytes of disk space.

## Quick start with Docker

1. Clone the repository and create your local configuration:

   ```bash
   git clone https://github.com/Dumdart/SmartHomeBridge.git
   cd SmartHomeBridge
   cp .env.example .env
   ```

2. Edit `.env`. At minimum, configure:

   ```dotenv
   DOOR_API_KEY=your-api-key
   DOOR_DEVICE_ID=your-device-id
   MQTT_HOST=192.168.1.20
   MQTT_USERNAME=smart_home_bridge
   MQTT_PASSWORD=change-me
   MQTT_BASE_TOPIC=smart-home-bridge
   CHICKEN_THREAT_ENABLED=false
   ```

3. Start the bridge:

   ```bash
   docker compose up -d
   ```

4. Inspect the service:

   ```bash
   docker compose ps
   docker compose logs -f smart-home-bridge
   ```

The default HTTP service is exposed on port `8080`. Change `HTTP_PORT` in
`.env` when that port is already in use.

### Optional experimental inference service

Set the camera and `CHICKEN_THREAT_*` values in `.env`, then start the inference
profile:

```bash
docker compose --profile inference up -d
```

To run only the inference service:

```bash
docker compose --profile inference up -d smart-home-inference
```

## Install from source

Create and activate a virtual environment, then install the project from the
repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

After editing `.env`, validate the configuration and start the service:

```bash
smart-home-bridge-config-check
smart-home-bridge
```

Useful commands:

```bash
smart-home-bridge-status
smart-home-bridge-door-command open_door
smart-home-bridge-door-command close_door
smart-home-bridge-door-command stop_door
smart-home-bridge-door-command get_door_state
```

## LoxBerry installation

This repository produces two independently installable LoxBerry archives:

| Plugin | Purpose | Status |
| --- | --- | --- |
| `OmletChickenDoorPlugin` | Door configuration, MQTT state, logs, and manual commands | Primary integration |
| `ChickenBarnCameraPlugin` | Camera and external inference configuration | Experimental |

Build all plugins:

```bash
python scripts/build_loxberry_plugin.py
```

Or build only the plugin you need:

```bash
python scripts/build_loxberry_plugin.py --plugin omlet-chicken-door
python scripts/build_loxberry_plugin.py --plugin chicken-barn-camera
```

The archives are written to:

```text
build/loxberry/omlet-chicken-door-loxberry.zip
build/loxberry/chicken-barn-camera-loxberry.zip
```

Upload the generated plugin archive in LoxBerry. Do not upload the GitHub source
archive or a ZIP of the repository root: LoxBerry requires `plugin.cfg` at the
archive root.

Both plugins install the shared bridge runtime, but each enables only its own
device domain. The door plugin reads LoxBerry's MQTT broker configuration and
adds the Omlet-specific settings and controls.

## Configuration

Plugin installation builds and validates a fresh versioned virtual environment,
then switches the stable `venv` link to it. This recreates the runtime after a
Debian/Python migration instead of reusing packages installed for an older
Python minor version. Runtime dependencies are installed from the pinned
`requirements-loxberry.txt` bundle before the application package is installed.

Inference dependencies such as Torch and Ultralytics can require multiple GB of
disk space, so run inference with Docker or install `.[inference]` manually on a
larger host. The LoxBerry web UI exposes the bridge lifecycle, config checks,
log tailing, and settings; manual door commands appear only in the door plugin.

Configuration comes from `.env` or process environment variables by default.
LoxBerry installations can instead use `SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry`.

Core settings:

| Variable | Required | Description |
| --- | --- | --- |
| `DOOR_API_KEY` | For door integration | Omlet API key |
| `DOOR_DEVICE_ID` | For door integration | Omlet door device ID |
| `MQTT_HOST` | Yes | MQTT broker hostname or IP address |
| `MQTT_USERNAME` | Yes by default | MQTT username |
| `MQTT_PASSWORD` | Yes by default | MQTT password |
| `MQTT_BASE_TOPIC` | Yes | Namespace only, for example `smart-home-bridge` |
| `MQTT_PORT` | No | MQTT broker port; see `.env.example` |
| `MQTT_USE_TLS` | No | Enable MQTT TLS; defaults to `false` |
| `DOOR_POLL_INTERVAL_SECONDS` | No | Door polling interval; defaults to `5` |
| `HTTP_HOST` | No | HTTP bind address; defaults to `0.0.0.0` |
| `HTTP_PORT` | No | HTTP port; defaults to `8080` |
| `LOG_LEVEL` | No | Runtime log level; defaults to `INFO` |

`MQTT_BASE_TOPIC` must contain only the namespace. The bridge appends its device
topics. Command, status, telemetry, and usage topics can be overridden
individually; the complete reference is in [.env.example](.env.example).

When the door integration is enabled, the bridge requests the complete Omlet
state immediately after connecting to MQTT and then once per polling interval.
Every successful response is republished as a retained heartbeat, even if the
state has not changed.

## Development

Install the development dependencies and run the test suite:

```bash
pip install -e ".[dev]"
pytest
```

Build the images directly when testing Docker changes:

```bash
docker build -t smart-home-bridge:local .
docker build -f Dockerfile.inference -t smart-home-inference:local .
```

For work on the experimental inference runtime:

```bash
pip install -e ".[inference]"
smart-home-inference
```

The model-training lifecycle is intentionally separate from deployment. Install
the locked ML environment with `uv sync --extra ml --locked`, then follow the
[chicken-threat ML workflow](ml/chicken_threat/README.md). Datasets, source
images, and candidate weights must not be committed.

## Security and safety

- Keep MQTT, camera, and HTTP endpoints on a trusted LAN.
- Use MQTT authentication and restrictive broker ACLs.
- Never commit `.env`, firmware `secrets.h`, API keys, passwords, camera tokens,
  broker details, or private model data.
- Treat door movement as safety-sensitive. Preserve a physical/manual override
  and verify the area around the door before issuing remote commands.
- Do not use the experimental camera model as the sole basis for protecting
  animals or triggering safety-critical automation.

## Troubleshooting

Start with the configuration checker and service logs:

```bash
smart-home-bridge-config-check
smart-home-bridge-status
docker compose logs -f smart-home-bridge
```

If MQTT state does not appear, verify the broker address, credentials, ACLs,
TLS setting, and base topic. If door polling fails, verify the Omlet API key and
device ID. LoxBerry deployment and runtime details are documented in
[TECHNICAL.MD](TECHNICAL.MD#loxone-and-loxberry).

## Contributing

Issues and focused pull requests are welcome. Keep changes small, follow the
existing architecture, add or update tests for behavior changes, and ensure the
full test suite passes before opening a pull request.

## License

This project is licensed under the MIT License.
