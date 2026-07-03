from __future__ import annotations

from collections.abc import Callable

from smart_home_bridge.bridge_devices.chicken_door import DoorGateway
from smart_home_bridge.bridge_devices.chicken_door.composition import (
    create_chicken_door_composition,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.composition import (
    create_chicken_thread_detector_composition,
)
from smart_home_bridge.bridge_devices.runtime import BridgeDeviceComposition
from smart_home_bridge.config import DoorApiConfig, app_config
from smart_home_bridge.infrastructure.omlet import OmletDoorClient


def create_bridge_device_compositions(
    config: app_config,
    door_gateway_factory: Callable[[DoorApiConfig], DoorGateway | None] = OmletDoorClient,
) -> tuple[BridgeDeviceComposition, ...]:
    device_compositions: list[BridgeDeviceComposition] = []
    if config.devices.is_enabled("chicken_door"):
        device_compositions.append(
            create_chicken_door_composition(config, door_gateway_factory),
        )
    if config.devices.is_enabled("chicken_thread_detector"):
        device_compositions.append(create_chicken_thread_detector_composition(config))

    return tuple(device_compositions)
