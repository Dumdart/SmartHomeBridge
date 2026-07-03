from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.composition import create_bridge_composition
from smart_home_bridge.config import (
    BridgeDevicesConfig,
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

    assert [device.key for device in composition.device_compositions] == [
        "chicken_door",
        "chicken_thread_detector",
    ]
    assert composition.door.position == door_position.UNKNOWN
    assert composition.door_controller.device is composition.door
    assert composition.threat_detector_controller.detector is composition.threat_detector
    assert composition.threat_inference_service.detector.config is composition.threat_model_config
    assert composition.command_topic == "loxone/chicken-door/command"
    assert composition.door_topics.status == "loxone/chicken-door/status"
    assert composition.door_topics.status_code == "loxone/chicken-door/status_code"
    assert composition.detector_topic == "loxone/chicken-thread-detector"


def test_thread_detector_runtime_exposes_enabled_threat_pipeline_as_lifecycle_service():
    config = _config(
        chicken_threat=ChickenThreatConfig(
            enabled=True,
            model_path="/models/chicken_threat_detector_best.pt",
            poll_interval_seconds=7,
        ),
    )

    composition = create_bridge_composition(config)
    runtime = _device_composition(composition, "chicken_thread_detector").create_runtime(
        lambda _: FakeMqttClient(),
    )
    pipeline = runtime.handles["chicken_threat_pipeline"]

    assert pipeline is not None
    assert pipeline.camera_client is composition.camera_client
    assert pipeline.inference_service is composition.threat_inference_service
    assert pipeline.detector_controller is composition.threat_detector_controller
    assert pipeline.poll_interval_seconds == 7
    assert runtime.background_services == (pipeline,)


def test_thread_detector_runtime_skips_disabled_threat_pipeline():
    composition = create_bridge_composition(
        _config(chicken_threat=ChickenThreatConfig(enabled=False)),
    )
    runtime = _device_composition(composition, "chicken_thread_detector").create_runtime(
        lambda _: FakeMqttClient(),
    )

    assert runtime.handles["chicken_threat_pipeline"] is None
    assert runtime.background_services == ()


def test_bridge_composition_uses_enabled_device_list():
    composition = create_bridge_composition(
        _config(devices=BridgeDevicesConfig(enabled=("chicken_door",))),
    )

    assert [device.key for device in composition.device_compositions] == ["chicken_door"]
    assert composition.door_controller.device is composition.door
    try:
        composition.threat_detector_controller
    except AttributeError:
        pass
    else:
        raise AssertionError("Expected disabled detector handles to be omitted")


def test_device_config_overrides_device_names_ids_and_topics():
    config = _config(
        devices=BridgeDevicesConfig(
            enabled=("chicken_door", "chicken_thread_detector"),
            configs={
                "chicken_door": _device_config(
                    "chicken_door",
                    device_id=42,
                    name="coop_door",
                    topics={"command": "coop/door/cmd", "status": "coop/door/state"},
                ),
                "chicken_thread_detector": _device_config(
                    "chicken_thread_detector",
                    device_id=43,
                    name="coop_detector",
                    topics={"detections": "coop/detector/detections"},
                ),
            },
        ),
    )

    composition = create_bridge_composition(config)

    assert composition.door.device_id == 42
    assert composition.door.name == "coop_door"
    assert composition.command_topic == "loxone/coop/door/cmd"
    assert composition.door_topics.status == "loxone/coop/door/state"
    assert composition.threat_detector.device_id == 43
    assert composition.threat_detector.name == "coop_detector"
    assert composition.detector_topic == "loxone/coop/detector/detections"


def _config(
    chicken_threat: ChickenThreatConfig | None = None,
    devices: BridgeDevicesConfig | None = None,
) -> app_config:
    return app_config(
        door_api=DoorApiConfig(
            api_key="api-key",
            device_id="device-id",
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
        devices=devices or BridgeDevicesConfig(),
    )


def _device_composition(composition, key):
    for device_composition in composition.device_compositions:
        if device_composition.key == key:
            return device_composition
    raise AssertionError(f"Expected device composition for {key}")


def _device_config(key, device_id, name, topics):
    from smart_home_bridge.config import BridgeDeviceConfig

    return BridgeDeviceConfig(
        key=key,
        device_id=device_id,
        name=name,
        topics=topics,
    )


class FakeMqttClient:
    async def connect(self, on_connect=None):
        pass

    async def disconnect(self, on_disconnect=None):
        pass

    async def publish(self, topic, payload, retain=False, on_publish=None):
        pass

    async def subscribe(self, topic, on_subscribe=None):
        pass

    def message_callback_add(self, topic, callback):
        pass
