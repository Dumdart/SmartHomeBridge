from dataclasses import dataclass

from loxone_bridge.bridge_devices.chicken_door import (
    chicken_door,
    door_controller,
    door_position,
)
from loxone_bridge.config import app_config
from loxone_bridge.infrastructure.api.http_gate import HttpGate
from loxone_bridge.services import ActivityLog, EnvSettingsService


@dataclass(frozen=True)
class GuiBridgeContext:
    config: app_config
    door: chicken_door
    door_controller: door_controller
    command_topic: str
    env_settings: EnvSettingsService
    activity_log: ActivityLog


def create_gui_bridge_context(
    config: app_config,
    env_settings: EnvSettingsService | None = None,
) -> GuiBridgeContext:
    door = chicken_door(1, "door", door_position.UNKNOWN)
    controller = door_controller(door, HttpGate(config.http))

    return GuiBridgeContext(
        config=config,
        door=door,
        door_controller=controller,
        command_topic=_build_topic(config.mqtt.base_topic, "chicken-door"),
        env_settings=env_settings or EnvSettingsService(),
        activity_log=ActivityLog(config.log_file_path),
    )


def _build_topic(base_topic: str, topic: str) -> str:
    return f"{base_topic.rstrip('/')}/{topic.strip('/')}"
