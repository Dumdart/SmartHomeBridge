# Repository Guidelines

## Project Structure & Module Organization

This Python package uses a `src` layout. Runtime code lives under `src/smart_home_bridge/`.

- `src/smart_home_bridge/core/`: device, command, and controller abstractions.
- `src/smart_home_bridge/bridge_devices/chicken_door/`: chicken door model, controller, messages, and MQTT callbacks.
- `src/smart_home_bridge/bridge_devices/chicken_thread_detector/`: camera inference pipeline, detector model integration, danger scoring, and MQTT callbacks.
- `src/smart_home_bridge/infrastructure/api/`: HTTP gateway code for vendor or diagnostic APIs.
- `src/smart_home_bridge/infrastructure/camera/`: ESP32-CAM HTTP client integration.
- `src/smart_home_bridge/infrastructure/mqtt/`: MQTT client, gate, and callback wiring.
- `src/smart_home_bridge/gui/`: optional PySide6 desktop diagnostics and control UI.
- `src/smart_home_bridge/services/`: shared support services such as activity logging and environment updates.
- `src/smart_home_bridge/config.py`: environment-backed configuration.
- `src/firmware/esp32cam_extention/`: ESP32-CAM firmware project and examples.
- `tests/`: pytest coverage by module or feature.
- `Dockerfile` and `docker-compose.yml`: containerized local/runtime deployment.

Do not commit generated artifacts such as `__pycache__/`, `.pytest_cache/`, build metadata, runtime logs, or local secrets.

## Build, Test, and Development Commands

- `pip install -e ".[dev]"`: install the package in editable mode with pytest.
- `pip install -e ".[gui]"`: install the optional desktop GUI dependencies.
- `pip install -e ".[inference]"`: install backend-only inference dependencies.
- `smart-home-bridge`: run the configured backend entry point.
- `smart-home-bridge-gui`: run the optional local diagnostics UI.
- `pytest`: run the full test suite.
- `docker compose up -d`: start the service using values from `.env`.
- `docker build -t smart-home-bridge:local .`: build the image directly.

Copy `.env.example` to `.env` before local runtime testing and set the MQTT, HTTP, camera, and detector values for your environment.

## Coding Style & Naming Conventions

Use Python 3.11+ idioms and follow the existing package structure before adding abstractions. Keep domain logic independent from MQTT, HTTP, GUI, camera, and vendor-specific concerns. Use 4-space indentation, `snake_case` for functions and modules, and `PascalCase` for classes.

Comments should explain non-obvious logic only, using the project convention `# Check ...`. Do not leave TODO comments, debug prints, or temporary scaffolding in committed code.

## Testing Guidelines

Tests use `pytest`. Name test files `test_*.py` and test functions `test_<behavior>()`. Prefer fast unit tests with fakes, as in `tests/test_http_gate.py`. Add or update tests whenever command handling, state mapping, configuration, MQTT callbacks, HTTP behavior, camera handling, detector scoring, or GUI behavior changes.

Run `pytest` before opening a pull request and fix failures in the same change.

## Commit & Pull Request Guidelines

This checkout does not include enough Git history to infer a repository-specific convention. Use concise, imperative subjects such as `Add HTTP gate error handling` or `Fix chicken door close command`.

Pull requests should include a summary, reason for the change, test results, and any configuration or deployment impact. Link related issues when available. For Loxone, MQTT, or diagnostics behavior, include the relevant topic, endpoint, or payload example.

## Security & Configuration Tips

Never commit real `.env` secrets, `secrets.h`, API credentials, MQTT passwords, broker details, camera addresses, or model/private data. Keep MQTT, HTTP, and camera endpoints LAN-only unless explicitly secured. Treat door movement commands as safety-sensitive: validate commands, publish confirmed state, and preserve manual override behavior.
