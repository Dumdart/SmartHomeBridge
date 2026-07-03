from dataclasses import dataclass
from collections.abc import Callable

from smart_home_bridge.bridge_devices.chicken_door import DoorGateway, chicken_door, door_controller
from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    chicken_thread_detector,
    chicken_thread_detector_controller,
)
from smart_home_bridge.bridge_devices.registry import create_bridge_device_compositions
from smart_home_bridge.composition import create_bridge_composition
from smart_home_bridge.config import DoorApiConfig, app_config
from smart_home_bridge.gui.threat_detection import GuiThreatScanService
from smart_home_bridge.services import ActivityLog, EnvSettingsService


@dataclass(frozen=True)
class GuiBridgeContext:
    config: app_config
    door: chicken_door
    door_controller: door_controller
    threat_detector: chicken_thread_detector
    threat_detector_controller: chicken_thread_detector_controller
    threat_scan_service: GuiThreatScanService
    command_topic: str
    detector_topic: str
    env_settings: EnvSettingsService
    activity_log: ActivityLog


def create_gui_bridge_context(
    config: app_config,
    env_settings: EnvSettingsService | None = None,
    door_gateway_factory: Callable[[DoorApiConfig], DoorGateway | None] | None = None,
) -> GuiBridgeContext:
    if door_gateway_factory is None:
        composition = create_bridge_composition(config)
    else:
        composition = create_bridge_composition(
            config,
            device_composition_factory=lambda config: create_bridge_device_compositions(
                config,
                door_gateway_factory,
            ),
        )

    return GuiBridgeContext(
        config=config,
        door=composition.door,
        door_controller=composition.door_controller,
        threat_detector=composition.threat_detector,
        threat_detector_controller=composition.threat_detector_controller,
        threat_scan_service=GuiThreatScanService(
            camera_client=composition.camera_client,
            inference_service=composition.threat_inference_service,
            detector_controller=composition.threat_detector_controller,
            source=config.camera.host,
        ),
        command_topic=composition.command_topic,
        detector_topic=composition.detector_topic,
        env_settings=env_settings or EnvSettingsService(),
        activity_log=ActivityLog(config.log_file_path),
    )
