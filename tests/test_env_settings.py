from loxone_bridge.config import HttpConfig, MqttConfig
from loxone_bridge.services import EnvSettingsService


def test_env_settings_saves_mqtt_and_http_config(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_BASE_URL=https://sensor.local",
                "DOOR_API_USERNAME=user",
                "DOOR_API_PASSWORD=access_password",
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
            username="loxone_bridge",
            password="new-password",
            base_topic="barn/chicken-door",
        ),
        http=HttpConfig(host="localhost", port=9000),
    )

    content = env_path.read_text()
    assert "DOOR_API_PASSWORD=access_password" in content
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
