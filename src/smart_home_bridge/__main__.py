import asyncio
import json
import logging
import os
import sys
from collections.abc import Callable
from typing import Any

from smart_home_bridge.bridge_devices.chicken_door.door_controller import (
    CLOSE_DOOR_COMMAND,
    GET_DOOR_STATE_COMMAND,
    OPEN_DOOR_COMMAND,
    STOP_DOOR_COMMAND,
)
from smart_home_bridge.bridge_devices.runtime import BridgeDeviceRuntime
from smart_home_bridge.bridge_devices.runtime import build_topic
from smart_home_bridge.composition import BridgeComposition, create_bridge_composition
from smart_home_bridge.config import MqttConfig, app_config, load_config, load_loxberry_config
from smart_home_bridge.infrastructure.mqtt.mqtt_client import MqttClient
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttAdapter
from smart_home_bridge.runtime_status import build_backend_status

logger = logging.getLogger(__name__)


class App:
    def __init__(
        self,
        config: app_config,
        mqtt_client_factory: Callable[[MqttConfig], MqttAdapter] = MqttClient,
        composition_factory: Callable[[app_config], BridgeComposition] = create_bridge_composition,
    ):
        self.name = "SmartHomeBridge"
        self.config = config

        self.composition = composition_factory(config)
        self.http_gate = self.composition.http_gate

        self.device_runtimes = tuple(
            device_composition.create_runtime(mqtt_client_factory)
            for device_composition in self.composition.device_compositions
        )
        self._handles = self._collect_handles(self.device_runtimes)
        self._handles.update(self.composition.handles)

        for name, value in self._handles.items():
            setattr(self, name, value)

    async def start(self):
        logger.info("Starting %s application.", self.name)

        for runtime in self.device_runtimes:
            await runtime.start()

    async def wait_forever(self):
        await asyncio.Event().wait()

    async def stop(self):
        try:
            logger.info("Stopping %s application.", self.name)
            for runtime in reversed(self.device_runtimes):
                await runtime.stop()

        except Exception as e:
            logger.exception("Error during shutdown: %s", e)

    def _collect_handles(
        self,
        device_runtimes: tuple[BridgeDeviceRuntime, ...],
    ) -> dict[str, Any]:
        handles: dict[str, Any] = {}
        for runtime in device_runtimes:
            handles.update(runtime.handles)
        return handles

    def status_snapshot(self) -> dict[str, Any]:
        return build_backend_status(self.config, self.device_runtimes)


async def main():
    app_config = load_app_config()
    configure_logging(app_config)
    application = App(app_config)

    try:
        await application.start()
        await application.wait_forever()
    finally:
        await application.stop()


def load_app_config() -> app_config:
    source = os.getenv("SMART_HOME_BRIDGE_CONFIG_SOURCE", "env").strip().lower()
    if source == "loxberry":
        return load_loxberry_config()
    if source == "env":
        return load_config()
    raise ValueError(
        "SMART_HOME_BRIDGE_CONFIG_SOURCE must be 'env' or 'loxberry'"
    )


def configure_logging(config: app_config):
    log_file_path = os.fspath(config.log_file_path)
    os.makedirs(os.path.dirname(log_file_path) or ".", exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
    if os.getenv("SMART_HOME_BRIDGE_CONFIG_SOURCE", "env").strip().lower() != "loxberry":
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def run():
    asyncio.run(main())


def status():
    application = App(load_app_config())
    print(json.dumps(application.status_snapshot(), indent=2, sort_keys=True))


def config_check():
    App(load_app_config())
    print(json.dumps({"ok": True}, sort_keys=True))


async def _publish_door_command(command: str):
    allowed_commands = {
        OPEN_DOOR_COMMAND,
        CLOSE_DOOR_COMMAND,
        STOP_DOOR_COMMAND,
        GET_DOOR_STATE_COMMAND,
    }
    if command not in allowed_commands:
        allowed = ", ".join(sorted(allowed_commands))
        raise ValueError(f"Unsupported door command '{command}'. Allowed: {allowed}")

    config = load_app_config()
    door_config = config.devices.for_device("chicken_door")
    command_topic = build_topic(
        config.mqtt.base_topic,
        door_config.topic("command", "chicken-door/command"),
    )
    client = MqttClient(config.mqtt)
    await client.connect()
    try:
        await client.publish(command_topic, command)
    finally:
        await client.disconnect()
    print(json.dumps({"published": True, "topic": command_topic, "command": command}))


def door_command():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: smart-home-bridge-door-command "
            "{open_door|close_door|stop_door|get_door_state}"
        )
    asyncio.run(_publish_door_command(sys.argv[1]))


if __name__ == "__main__":
    run()
