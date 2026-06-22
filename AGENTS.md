# Repository Guidelines

## Project Structure & Module Organization

This Python package uses a `src` layout. Runtime code lives under `src/loxone_bridge/`.

- `src/loxone_bridge/core/`: domain concepts such as devices, commands, and controllers.
- `src/loxone_bridge/bridge_devices/chicken_door/`: chicken door device model, controller, and MQTT callbacks.
- `src/loxone_bridge/infrastructure/api/`: HTTP gateway code for vendor or diagnostic APIs.
- `src/loxone_bridge/infrastructure/mqtt/`: MQTT client, gate, and callback integration.
- `src/loxone_bridge/config.py`: environment-backed configuration.
- `tests/`: pytest tests by module or feature.
- `Dockerfile` and `docker-compose.yml`: containerized local/runtime deployment.

Do not commit generated artifacts such as `__pycache__/`, `.pytest_cache/`, or build metadata.

## Build, Test, and Development Commands

- `pip install -e ".[dev]"`: install the package in editable mode with pytest.
- `loxone-bridge`: run the configured application entry point.
- `pytest`: run the full test suite.
- `docker compose up -d`: start the service using values from `.env`.
- `docker build -t loxone-bridge:local .`: build the image directly.

Copy `.env.example` to `.env` before local runtime testing and set MQTT/HTTP values for your environment.

## Coding Style & Naming Conventions

Use Python 3.11+ idioms and follow the existing package structure before adding abstractions. Keep domain logic independent from MQTT, HTTP, and vendor-specific concerns. Use 4-space indentation, `snake_case` for functions and modules, and `PascalCase` for classes.

Comments should explain non-obvious logic only, using the project convention `# Check ...`. Do not leave TODO comments, debug prints, or temporary scaffolding in committed code.

## Testing Guidelines

Tests use `pytest`. Name test files `test_*.py` and test functions `test_<behavior>()`. Prefer fast unit tests with fakes, as in `tests/test_http_gate.py`. Add or update tests whenever command handling, state mapping, configuration, MQTT callbacks, or HTTP behavior changes.

Run `pytest` before opening a pull request and fix failures in the same change.

## Commit & Pull Request Guidelines

This checkout does not include Git history, so no repository-specific convention can be inferred. Use concise, imperative subjects such as `Add HTTP gate error handling` or `Fix chicken door close command`.

Pull requests should include a summary, reason for the change, test results, and any configuration or deployment impact. Link related issues when available. For Loxone, MQTT, or diagnostics behavior, include the relevant topic, endpoint, or payload example.

## Security & Configuration Tips

Never commit real `.env` secrets, API credentials, MQTT passwords, or broker details. Keep MQTT and HTTP endpoints LAN-only unless explicitly secured. Treat door movement commands as safety-sensitive: validate commands, publish confirmed state, and preserve manual override behavior.
