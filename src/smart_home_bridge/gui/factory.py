from dataclasses import dataclass

from smart_home_bridge.bridge_devices.chicken_door import (
    chicken_door,
    door_controller,
    door_position,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatInferenceService,
    DangerScorer,
    LocalChickenThreadDetector,
    chicken_thread_detector,
    chicken_thread_detector_controller,
    default_model_config,
)
from smart_home_bridge.config import app_config
from smart_home_bridge.infrastructure.api.http_gate import HttpGate
from smart_home_bridge.infrastructure.camera import CameraClient
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
) -> GuiBridgeContext:
    door = chicken_door(1, "door", door_position.UNKNOWN)
    controller = door_controller(door, HttpGate(config.http))
    model_config = default_model_config(config.chicken_threat.model_path)
    threat_detector = chicken_thread_detector(2, "chicken_thread_detector")
    threat_controller = chicken_thread_detector_controller(
        threat_detector,
        danger_scorer=DangerScorer(model_config),
    )
    camera_client = CameraClient(config.camera)
    inference_service = ChickenThreatInferenceService(
        LocalChickenThreadDetector(model_config),
    )

    return GuiBridgeContext(
        config=config,
        door=door,
        door_controller=controller,
        threat_detector=threat_detector,
        threat_detector_controller=threat_controller,
        threat_scan_service=GuiThreatScanService(
            camera_client=camera_client,
            inference_service=inference_service,
            detector_controller=threat_controller,
            source=config.camera.host,
        ),
        command_topic=_build_topic(config.mqtt.base_topic, "chicken-door"),
        detector_topic=_build_topic(config.mqtt.base_topic, "chicken-thread-detector"),
        env_settings=env_settings or EnvSettingsService(),
        activity_log=ActivityLog(config.log_file_path),
    )


def _build_topic(base_topic: str, topic: str) -> str:
    return f"{base_topic.rstrip('/')}/{topic.strip('/')}"
