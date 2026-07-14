from smart_home_bridge.bridge_devices.runtime import (
    BridgeDeviceMqttBinding,
    BridgeDeviceRuntime,
)
from smart_home_bridge.config import (
    BridgeDevicesConfig,
    CameraConfig,
    ChickenThreatConfig,
    DoorApiConfig,
    HttpConfig,
    MqttConfig,
    app_config,
)
from smart_home_bridge.runtime_status import build_backend_status


def test_backend_status_redacts_secrets_and_reports_topics():
    config = app_config(
        door_api=DoorApiConfig(api_key="door-secret", device_id="door-id"),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=1883,
            username="mqtt-user",
            password="mqtt-secret",
            base_topic="smart-home-bridge",
            use_tls=True,
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        camera=CameraConfig(host="esp32cam.local", auth_token="camera-secret"),
        chicken_threat=ChickenThreatConfig(enabled=True),
        devices=BridgeDevicesConfig(enabled=("chicken_door",)),
    )
    runtime = BridgeDeviceRuntime(
        name="door",
        mqtt_config=config.mqtt,
        mqtt_bindings=(
            BridgeDeviceMqttBinding(
                name="commands",
                topic="chicken-door/command",
                gate=object(),
                publish_topics=("smart-home-bridge/chicken-door/status",),
            ),
        ),
    )
    runtime.mqtt_running = True

    status = build_backend_status(config, (runtime,))

    assert status["mqtt"]["host"] == "mqtt.local"
    assert status["mqtt"]["password_configured"] is True
    assert status["camera"]["auth_token_configured"] is True
    assert status["door_polling"] == {
        "enabled": True,
        "poll_interval_seconds": 5.0,
        "running": False,
    }
    assert status["devices"]["runtimes"][0]["mqtt_bindings"][0]["topic"] == (
        "smart-home-bridge/chicken-door/command"
    )
    status_text = repr(status)
    assert "mqtt-secret" not in status_text
    assert "door-secret" not in status_text
    assert "camera-secret" not in status_text
