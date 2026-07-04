from smart_home_bridge.config import (
    BridgeDevicesConfig,
    CameraConfig,
    ChickenThreatConfig,
    DoorApiConfig,
    HttpConfig,
    MqttConfig,
    app_config,
)
from smart_home_bridge.services import EnvSettingsService


def test_env_settings_saves_mqtt_and_http_config(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=old-broker",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=old-user",
                "MQTT_PASSWORD=old-password",
                "MQTT_BASE_TOPIC=old/topic",
                "HTTP_HOST=0.0.0.0",
                "HTTP_PORT=8080",
                "LOG_LEVEL=DEBUG",
            ]
        )
        + "\n"
    )
    service = EnvSettingsService(env_path)

    config = service.save_mqtt_http(
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="smart_home_bridge",
            password="new-password",
            base_topic="barn/chicken-door",
        ),
        http=HttpConfig(host="localhost", port=9000),
    )

    content = env_path.read_text()
    assert "DOOR_API_KEY=api-key" in content
    assert "DOOR_DEVICE_ID=device-id" in content
    assert "LOG_LEVEL=DEBUG" in content
    assert "MQTT_HOST=mqtt.local" in content
    assert "MQTT_PORT=8883" in content
    assert "MQTT_BASE_TOPIC=barn/chicken-door" in content
    assert "HTTP_HOST=localhost" in content
    assert "HTTP_PORT=9000" in content
    assert config.mqtt.host == "mqtt.local"
    assert config.mqtt.port == 8883
    assert config.http.host == "localhost"
    assert config.http.port == 9000


def test_env_settings_rejects_invalid_ports(tmp_path):
    service = EnvSettingsService(tmp_path / ".env")

    try:
        service.save_mqtt_http(
            mqtt=MqttConfig(
                host="mqtt.local",
                port=0,
                username="user",
                password="password",
                base_topic="topic",
            ),
            http=HttpConfig(host="localhost", port=8080),
        )
    except ValueError as exc:
        assert str(exc) == "MQTT_PORT must be between 1 and 65535"
    else:
        raise AssertionError("Expected invalid MQTT port to be rejected")


def test_env_settings_saves_critical_runtime_settings(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=old-broker",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=old-user",
                "MQTT_PASSWORD=old-password",
                "MQTT_BASE_TOPIC=old/topic",
            ]
        )
        + "\n"
    )
    service = EnvSettingsService(env_path)

    config = service.save_critical_settings(
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="smart-home-bridge",
            use_tls=True,
        ),
        devices=BridgeDevicesConfig(enabled=("chicken_door",)),
        camera=CameraConfig(host="esp32cam.local", port=81, auth_token="camera-token"),
        chicken_threat=ChickenThreatConfig(
            enabled=True,
            model_path="/models/chicken.pt",
            poll_interval_seconds=15,
        ),
        log_level="DEBUG",
    )

    content = env_path.read_text()
    assert "BRIDGE_DEVICES_ENABLED=chicken_door" in content
    assert "CAMERA_HOST=esp32cam.local" in content
    assert "CAMERA_PORT=81" in content
    assert "CAMERA_AUTH_TOKEN=camera-token" in content
    assert "CHICKEN_THREAT_ENABLED=true" in content
    assert "CHICKEN_THREAT_POLL_INTERVAL_SECONDS=15" in content
    assert "LOG_LEVEL=DEBUG" in content
    assert config.mqtt.use_tls is True
    assert config.devices.enabled == ("chicken_door",)
    assert config.camera.host == "esp32cam.local"
    assert config.chicken_threat.enabled is True
