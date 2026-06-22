# Smart Home Bridge

Smart Home Bridge helps connect local smart home systems with devices that do not expose a clean or compatible integration interface. Many smart home platforms provide customizable apps and controls, while individual devices often rely on vendor-specific APIs that are difficult to integrate directly.

This project provides a configurable bridge between those devices and MQTT. Smart home systems can then read state and send commands through MQTT topics instead of talking to each vendor API directly.

Smart Home Bridge can run from the console or inside Docker. Custom devices can be defined and wired into the same bridge pattern.

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

### MQTT Broker

* Provide the local message bus between the backend and Loxone
* Recommended: Mosquitto
* Run on the same LAN as the Miniserver
* Use authentication and restricted ACLs

## Development

1. Configure environment variables in `.env` or set them directly in the shell. See `.env.example` for the available settings.

2. Install dependencies:

```bash
pip install -e ".[dev]"
```

Install the optional desktop GUI dependencies when you want the local control
panel:

```bash
pip install -e ".[gui]"
```

3. Run the backend from the repository root:

```bash
python .\src\loxone_bridge\__main__.py
```

Run the PySide6 GUI:

```bash
loxone-bridge-gui
```

The GUI includes an Environment Settings panel for MQTT and HTTP settings. Save
updates writes those values to `.env`; restart the backend service for a running
bridge process to pick up the changed environment.

4. Run tests:

```bash
pytest
```

5. Run with Docker Compose:

```bash
docker compose up -d
```

Docker runs only the bridge service logic. The image installs the base package
without the optional PySide6 GUI dependencies, and the container command is
`loxone-bridge`.

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
