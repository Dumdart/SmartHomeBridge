from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.composition import create_bridge_composition
from smart_home_bridge.config import (
    CameraConfig,
    ChickenThreatConfig,
    DoorApiConfig,
    HttpConfig,
    MqttConfig,
    app_config,
)


def test_bridge_composition_wires_shared_devices_and_topics():
    config = _config()

    composition = create_bridge_composition(config)

    assert composition.door.position == door_position.UNKNOWN
    assert composition.door_controller.device is composition.door
    assert composition.threat_detector_controller.detector is composition.threat_detector
    assert composition.threat_inference_service.detector.config is composition.threat_model_config
    assert composition.command_topic == "loxone/chicken-door"
    assert composition.detector_topic == "loxone/chicken-thread-detector"


def test_bridge_composition_creates_enabled_threat_pipeline():
    config = _config(
        chicken_threat=ChickenThreatConfig(
            enabled=True,
            model_path="/models/chicken_threat_detector_best.pt",
            poll_interval_seconds=7,
        ),
    )

    composition = create_bridge_composition(config)
    pipeline = composition.create_chicken_threat_pipeline()

    assert pipeline is not None
    assert pipeline.camera_client is composition.camera_client
    assert pipeline.inference_service is composition.threat_inference_service
    assert pipeline.detector_controller is composition.threat_detector_controller
    assert pipeline.poll_interval_seconds == 7


def test_bridge_composition_skips_disabled_threat_pipeline():
    composition = create_bridge_composition(
        _config(chicken_threat=ChickenThreatConfig(enabled=False)),
    )

    assert composition.create_chicken_threat_pipeline() is None


def _config(
    chicken_threat: ChickenThreatConfig | None = None,
) -> app_config:
    return app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
        ),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="loxone",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        camera=CameraConfig(host="esp32cam.local", port=80),
        chicken_threat=chicken_threat or ChickenThreatConfig(enabled=True),
    )
