from dataclasses import dataclass

from smart_home_bridge.bridge_devices.chicken_door import (
    chicken_door,
    door_controller,
    door_position,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatDetectionPipeline,
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
from smart_home_bridge.models import ChickenThreadModelConfig

CHICKEN_DOOR_TOPIC = "chicken-door"
CHICKEN_THREAD_DETECTOR_TOPIC = "chicken-thread-detector"


@dataclass(frozen=True)
class BridgeComposition:
    config: app_config
    door: chicken_door
    http_gate: HttpGate
    door_controller: door_controller
    threat_detector: chicken_thread_detector
    threat_model_config: ChickenThreadModelConfig
    threat_detector_controller: chicken_thread_detector_controller
    camera_client: CameraClient
    threat_inference_service: ChickenThreatInferenceService
    command_topic: str
    detector_topic: str

    def create_chicken_threat_pipeline(self) -> ChickenThreatDetectionPipeline | None:
        if not self.config.chicken_threat.enabled:
            return None

        return ChickenThreatDetectionPipeline(
            camera_client=self.camera_client,
            inference_service=self.threat_inference_service,
            detector_controller=self.threat_detector_controller,
            poll_interval_seconds=self.config.chicken_threat.poll_interval_seconds,
            source=self.config.camera.host,
        )


def create_bridge_composition(config: app_config) -> BridgeComposition:
    door = chicken_door(1, "door", door_position.UNKNOWN)
    http_gate = HttpGate(config.http)
    controller = door_controller(door)

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

    return BridgeComposition(
        config=config,
        door=door,
        http_gate=http_gate,
        door_controller=controller,
        threat_detector=threat_detector,
        threat_model_config=model_config,
        threat_detector_controller=threat_controller,
        camera_client=camera_client,
        threat_inference_service=inference_service,
        command_topic=build_topic(config.mqtt.base_topic, CHICKEN_DOOR_TOPIC),
        detector_topic=build_topic(config.mqtt.base_topic, CHICKEN_THREAD_DETECTOR_TOPIC),
    )


def build_topic(base_topic: str, topic: str) -> str:
    return f"{base_topic.rstrip('/')}/{topic.strip('/')}"
