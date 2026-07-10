# Agent Instructions

## General

- Work in focused, atomic steps. Prefer small, testable changes over broad refactors.
- Follow the existing composition and adapter patterns before introducing new abstractions.
- Keep domain logic independent from MQTT, HTTP, GUI, camera, vendor, and LoxBerry concerns.
- Always run the relevant tests after changes and fix failures before opening a PR.
- Do not commit generated artifacts, runtime logs, local secrets, model data, or temporary scaffolding.
- Do not leave TODO comments or debug output in committed code.
- Explain non-obvious logic with comments beginning `# Check ...` (or `// Check ...` in PHP/C++).

## Project Structure

This Python package uses a `src` layout.

- `src/smart_home_bridge/`: bridge runtime, CLI, configuration, composition, devices, adapters, services, and optional GUI.
- `src/smart_home_bridge/core/`: shared device, command, controller, and runtime abstractions.
- `src/smart_home_bridge/bridge_devices/chicken_door/`: Omlet door model, controller, gateway, MQTT callbacks, and publisher.
- `src/smart_home_bridge/bridge_devices/chicken_thread_detector/`: detection input, camera polling, inference client, scoring, and MQTT callbacks.
- `src/smart_home_bridge/infrastructure/`: MQTT, HTTP, camera, and Omlet integrations.
- `src/smart_home_bridge/services/`: activity logging, environment updates, and MQTT usage reporting.
- `src/smart_home_inference/`: separate HTTP inference service, model registry, image validation, and YOLO detector.
- `src/smart_home_contracts/`: shared detection-frame and threat-assessment contracts.
- `src/firmware/esp32cam_extention/`: ESP32-CAM PlatformIO firmware and examples.
- `deploy/loxberry/shared/`: shared LoxBerry lifecycle hooks, service control, configuration UI, and MQTT seed files.
- `deploy/loxberry/plugins/`: per-device LoxBerry manifests, settings, and web UI profiles.
- `scripts/build_loxberry_plugin.py`: manifest-driven LoxBerry ZIP builder.
- `tests/`: pytest coverage for runtime, bridge devices, inference, GUI, packaging, and LoxBerry behavior.

The bridge and inference service are separate processes. The bridge calls the inference HTTP API when camera threat polling is enabled; it does not load YOLO models itself. Threat assessment must not autonomously move the chicken door.

## Development Commands

Install the package and the relevant optional dependencies from the repository root:

```bash
pip install -e ".[dev]"
pip install -e ".[gui]"       # optional desktop diagnostics
pip install -e ".[inference]" # optional HTTP inference backend
```

Useful entry points:

```bash
smart-home-bridge
smart-home-inference
smart-home-bridge-gui
smart-home-bridge-status
smart-home-bridge-config-check
smart-home-bridge-door-command open_door
```

Run tests with `pytest`. Build LoxBerry archives with:

```bash
python scripts/build_loxberry_plugin.py
python scripts/build_loxberry_plugin.py --plugin omlet-chicken-door
python scripts/build_loxberry_plugin.py --plugin chicken-barn-camera
```

Archives are generated below `build/loxberry/`; do not commit them. For Docker, use `docker compose up -d` for the bridge, `docker compose --profile inference up -d` for both services, or `docker compose --profile inference up -d smart-home-inference` for inference only. The GUI is not installed in the runtime images.

Copy `.env.example` to `.env` for local runtime testing. Use `SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry` only for LoxBerry configuration; normal development uses `.env` and environment variables.

## Coding and Testing Conventions

- Use Python 3.11+ idioms, 4-space indentation, `snake_case` functions/modules, and `PascalCase` classes.
- Preserve the existing `BridgeDeviceComposition` / `BridgeDeviceRuntime` lifecycle and dependency injection patterns.
- Validate commands and external payloads at their boundaries. Retained MQTT commands and stale detector frames must not be replayed as actions.
- Keep credentials and tokens redacted in status, logs, diagnostics, and LoxBerry output.
- Add or update fast unit tests whenever command handling, state mapping, configuration, MQTT callbacks, HTTP behavior, camera handling, inference, GUI behavior, packaging, or LoxBerry UI behavior changes.
- Prefer fakes and focused tests over live MQTT brokers, vendor APIs, cameras, or model downloads.

## LoxBerry and Configuration Safety

- Treat door movement commands as safety-sensitive: accept only the manifest-enabled commands, publish confirmed state, and preserve manual override behavior.
- Keep the two LoxBerry plugin profiles isolated: `omlet_chicken_door` enables `chicken_door`; `chicken_barn_camera` enables `chicken_thread_detector` and must reject door commands.
- The shared LoxBerry control script supports `start`, `stop`, `restart`, `status`, `dump-config`, and validated door commands. Inference is an external service and is not managed by the plugin.
- Never commit `.env`, API credentials, MQTT passwords, camera tokens, firmware `secrets.h`, private model data, or broker/camera endpoints intended to remain private.
- Keep MQTT, camera, bridge HTTP, and inference endpoints LAN-only unless explicitly secured.

## Commit and Pull Request Guidance

Use concise imperative commit subjects, for example `Fix chicken door close command`. PR descriptions should summarize the change, reason, tests run, and any configuration, MQTT topic, endpoint, packaging, or deployment impact.
