import json

from smart_home_bridge.config import (
    DEFAULT_CHICKEN_THREAT_INFERENCE_URL,
    load_config,
    load_config_from_environment,
    load_loxberry_config,
)


def test_load_config_reads_log_file_path(tmp_path):
    env_path = tmp_path / ".env"
    log_file_path = tmp_path / "bridge.log"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
                "MQTT_USE_TLS=true",
                "HTTP_HOST=localhost",
                "HTTP_PORT=8080",
                "LOG_LEVEL=DEBUG",
                f"LOG_FILE_PATH={log_file_path}",
            ]
        )
        + "\n"
    )

    config = load_config(str(env_path), override=True)

    assert config.log_file_path == str(log_file_path)
    assert config.mqtt.use_tls is True


def test_load_config_reads_enabled_omlet_webhook(tmp_path, monkeypatch):
    monkeypatch.setenv("OMLET_WEBHOOK_ENABLED", "false")
    monkeypatch.setenv("OMLET_WEBHOOK_TOKEN", "")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
                "OMLET_WEBHOOK_ENABLED=true",
                "OMLET_WEBHOOK_TOKEN=0123456789abcdef0123456789abcdef",
            ]
        )
        + "\n"
    )

    config = load_config(str(env_path), override=True)

    assert config.omlet_webhook.enabled is True
    assert config.omlet_webhook.token == "0123456789abcdef0123456789abcdef"


def test_load_config_rejects_short_enabled_omlet_webhook_token(tmp_path, monkeypatch):
    monkeypatch.setenv("OMLET_WEBHOOK_ENABLED", "false")
    monkeypatch.setenv("OMLET_WEBHOOK_TOKEN", "")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
                "OMLET_WEBHOOK_ENABLED=true",
                "OMLET_WEBHOOK_TOKEN=short-token",
            ]
        )
        + "\n"
    )

    try:
        load_config(str(env_path), override=True)
    except ValueError as exc:
        assert "at least 32 characters" in str(exc)
    else:
        raise AssertionError("Expected a short enabled webhook token to be rejected")


def test_load_config_from_environment_ignores_dotenv_file(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=file-api-key",
                "DOOR_DEVICE_ID=file-device-id",
                "MQTT_HOST=file-mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=file-user",
                "MQTT_PASSWORD=file-password",
                "MQTT_BASE_TOPIC=file-topic",
            ]
        )
        + "\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOOR_API_KEY", "env-api-key")
    monkeypatch.setenv("DOOR_DEVICE_ID", "env-device-id")
    monkeypatch.setenv("MQTT_HOST", "env-mqtt.local")
    monkeypatch.setenv("MQTT_PORT", "8883")
    monkeypatch.setenv("MQTT_USERNAME", "env-user")
    monkeypatch.setenv("MQTT_PASSWORD", "env-password")
    monkeypatch.setenv("MQTT_BASE_TOPIC", "env-topic")

    config = load_config_from_environment()

    assert config.door_api.api_key == "env-api-key"
    assert config.door_api.device_id == "env-device-id"
    assert config.mqtt.host == "env-mqtt.local"
    assert config.mqtt.port == 8883
    assert config.mqtt.username == "env-user"
    assert config.mqtt.password == "env-password"
    assert config.mqtt.base_topic == "env-topic"


def test_load_config_reads_independent_camera_and_threat_settings(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
                "CAMERA_HOST=esp32cam.local",
                "CAMERA_PORT=80",
                "CAMERA_JPG_ENDPOINT=/jpg",
                "CAMERA_HEALTH_ENDPOINT=/health",
                "CAMERA_TIMEOUT_SECONDS=2.5",
                "CAMERA_MAX_JPEG_BYTES=123456",
                "CAMERA_AUTH_TOKEN=camera-token",
                "CHICKEN_THREAT_ENABLED=true",
                "CHICKEN_THREAT_INFERENCE_URL=http://inference.local:8090/v1/chicken-threat/infer",
                "CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS=12",
                "CHICKEN_THREAT_POLL_INTERVAL_SECONDS=7.5",
            ]
        )
        + "\n"
    )

    config = load_config(str(env_path), override=True)

    assert config.camera.host == "esp32cam.local"
    assert config.camera.port == 80
    assert config.camera.jpg_endpoint == "/jpg"
    assert config.camera.health_endpoint == "/health"
    assert config.camera.timeout_seconds == 2.5
    assert config.camera.max_jpeg_bytes == 123456
    assert config.camera.auth_token == "camera-token"
    assert config.chicken_threat.enabled is True
    assert (
        config.chicken_threat.inference_url
        == "http://inference.local:8090/v1/chicken-threat/infer"
    )
    assert config.chicken_threat.inference_timeout_seconds == 12
    assert config.chicken_threat.poll_interval_seconds == 7.5


def test_load_config_reads_bridge_device_settings(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
                "BRIDGE_DEVICES_ENABLED=chicken_door",
                "CHICKEN_DOOR_BRIDGE_ID=42",
                "CHICKEN_DOOR_BRIDGE_NAME=coop_door",
                "CHICKEN_DOOR_COMMAND_TOPIC=coop/door/cmd",
                "CHICKEN_DOOR_STATUS_TOPIC=coop/door/state",
                "CHICKEN_THREAD_DETECTOR_BRIDGE_ID=43",
                "CHICKEN_THREAD_DETECTOR_BRIDGE_NAME=coop_detector",
                "CHICKEN_THREAD_DETECTOR_TOPIC=coop/detector/detections",
            ]
        )
        + "\n"
    )

    config = load_config(str(env_path), override=True)

    assert config.devices.enabled == ("chicken_door",)
    assert config.devices.is_enabled("chicken_door") is True
    assert config.devices.is_enabled("chicken_thread_detector") is False
    door_config = config.devices.for_device("chicken_door")
    detector_config = config.devices.for_device("chicken_thread_detector")
    assert door_config.device_id == 42
    assert door_config.name == "coop_door"
    assert door_config.topic("command", "") == "coop/door/cmd"
    assert door_config.topic("status", "") == "coop/door/state"
    assert detector_config.device_id == 43
    assert detector_config.name == "coop_detector"
    assert detector_config.topic("detections", "") == "coop/detector/detections"


def test_load_config_disables_chicken_threat_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("CHICKEN_THREAT_ENABLED", raising=False)
    monkeypatch.delenv("CHICKEN_THREAT_INFERENCE_URL", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
            ]
        )
        + "\n"
    )

    config = load_config(str(env_path), override=True)

    assert config.chicken_threat.enabled is False
    assert config.chicken_threat.inference_url == DEFAULT_CHICKEN_THREAT_INFERENCE_URL


def test_load_config_requires_door_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("DOOR_API_KEY", raising=False)
    monkeypatch.delenv("DOOR_DEVICE_ID", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_DEVICE_ID=device-id",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
            ]
        )
        + "\n"
    )

    try:
        load_config(str(env_path), override=True)
    except ValueError as exc:
        assert str(exc) == "Missing required environment variable: DOOR_API_KEY"
    else:
        raise AssertionError("Expected missing DOOR_API_KEY to be rejected")


def test_load_config_requires_door_device_id(tmp_path, monkeypatch):
    monkeypatch.delenv("DOOR_API_KEY", raising=False)
    monkeypatch.delenv("DOOR_DEVICE_ID", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_KEY=api-key",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
            ]
        )
        + "\n"
    )

    try:
        load_config(str(env_path), override=True)
    except ValueError as exc:
        assert str(exc) == "Missing required environment variable: DOOR_DEVICE_ID"
    else:
        raise AssertionError("Expected missing DOOR_DEVICE_ID to be rejected")


def test_load_config_does_not_require_door_credentials_for_camera_only(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("DOOR_API_KEY", raising=False)
    monkeypatch.delenv("DOOR_DEVICE_ID", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
                "BRIDGE_DEVICES_ENABLED=chicken_thread_detector",
            ]
        )
        + "\n"
    )

    config = load_config(str(env_path), override=True)

    assert config.door_api.api_key == ""
    assert config.door_api.device_id == ""
    assert config.devices.enabled == ("chicken_thread_detector",)


def test_load_loxberry_config_reads_mqtt_json_and_plugin_ini(tmp_path):
    home_dir = tmp_path / "loxberry"
    plugin_config_dir = tmp_path / "config"
    mqtt_dir = home_dir / "config" / "system"
    bridge_dir = plugin_config_dir / "smarthomebridge"
    mqtt_dir.mkdir(parents=True)
    bridge_dir.mkdir(parents=True)
    (mqtt_dir / "general.json").write_text(
        json.dumps(
            {
                "mqtt": {
                    "host": "loxberry-mqtt.local",
                    "port": 1884,
                    "username": "mqtt-user",
                    "password": "mqtt-password",
                    "use_tls": True,
                }
            }
        )
    )
    (bridge_dir / "smart-home-bridge.ini").write_text(
        "\n".join(
            [
                "[smart-home-bridge]",
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_BASE_TOPIC=smart-home-bridge",
                "BRIDGE_DEVICES_ENABLED=chicken_thread_detector",
                "CAMERA_HOST=esp32cam.local",
                "CAMERA_PORT=81",
                "CHICKEN_THREAT_ENABLED=true",
                "CHICKEN_THREAT_INFERENCE_URL=http://127.0.0.1:8090/v1/chicken-threat/infer",
                "CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS=9",
                "CHICKEN_THREAT_POLL_INTERVAL_SECONDS=12.5",
                "LOG_LEVEL=DEBUG",
            ]
        )
        + "\n"
    )

    config = load_loxberry_config(home_dir, plugin_config_dir)

    assert config.mqtt.host == "loxberry-mqtt.local"
    assert config.mqtt.port == 1884
    assert config.mqtt.username == "mqtt-user"
    assert config.mqtt.password == "mqtt-password"
    assert config.mqtt.base_topic == "smart-home-bridge"
    assert config.mqtt.use_tls is True
    assert config.devices.enabled == ("chicken_thread_detector",)
    assert config.camera.host == "esp32cam.local"
    assert config.camera.port == 81
    assert config.chicken_threat.enabled is True
    assert (
        config.chicken_threat.inference_url
        == "http://127.0.0.1:8090/v1/chicken-threat/infer"
    )
    assert config.chicken_threat.inference_timeout_seconds == 9
    assert config.chicken_threat.poll_interval_seconds == 12.5


def test_load_loxberry_config_resolves_default_log_file_to_plugin_log_dir(
    tmp_path,
    monkeypatch,
):
    home_dir = tmp_path / "loxberry"
    plugin_config_dir = tmp_path / "config"
    loxberry_log_dir = tmp_path / "logs"
    mqtt_dir = home_dir / "config" / "system"
    bridge_dir = plugin_config_dir / "smarthomebridge"
    mqtt_dir.mkdir(parents=True)
    bridge_dir.mkdir(parents=True)
    monkeypatch.setenv("LBPLOG", str(loxberry_log_dir))
    (mqtt_dir / "general.json").write_text(
        json.dumps({"mqtt": {"host": "loxberry-mqtt.local", "port": 1883}})
    )
    (bridge_dir / "smart-home-bridge.ini").write_text(
        "\n".join(
            [
                "[smart-home-bridge]",
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_BASE_TOPIC=smart-home-bridge",
                "LOG_FILE_PATH=logs/smart-home-bridge.log",
            ]
        )
        + "\n"
    )

    config = load_loxberry_config(home_dir, plugin_config_dir)

    assert config.log_file_path == str(
        loxberry_log_dir / "smarthomebridge" / "smart-home-bridge.log"
    )


def test_load_loxberry_config_accepts_gateway_mqtt_fields_without_credentials(tmp_path):
    home_dir = tmp_path / "loxberry"
    plugin_config_dir = tmp_path / "config"
    mqtt_dir = home_dir / "config" / "system"
    bridge_dir = plugin_config_dir / "smarthomebridge"
    mqtt_dir.mkdir(parents=True)
    bridge_dir.mkdir(parents=True)
    (mqtt_dir / "general.json").write_text(
        json.dumps(
            {
                "Mqtt": {
                    "Brokerhost": "loxberry-mqtt.local",
                    "Brokerport": "1883",
                    "Brokeruser": "",
                    "Brokerpass": "",
                    "Udpinport": "11884",
                }
            }
        )
    )
    (bridge_dir / "smart-home-bridge.ini").write_text(
        "\n".join(
            [
                "[smart-home-bridge]",
                "DOOR_API_KEY=api-key",
                "DOOR_DEVICE_ID=device-id",
                "MQTT_BASE_TOPIC=smart-home-bridge",
            ]
        )
        + "\n"
    )

    config = load_loxberry_config(home_dir, plugin_config_dir)

    assert config.mqtt.host == "loxberry-mqtt.local"
    assert config.mqtt.port == 1883
    assert config.mqtt.username == ""
    assert config.mqtt.password == ""


def test_load_loxberry_config_uses_selected_plugin_folder(tmp_path, monkeypatch):
    home_dir = tmp_path / "loxberry"
    plugin_config_dir = tmp_path / "config"
    log_dir = tmp_path / "logs"
    mqtt_dir = home_dir / "config" / "system"
    bridge_dir = plugin_config_dir / "chickenbarncamera"
    mqtt_dir.mkdir(parents=True)
    bridge_dir.mkdir(parents=True)
    monkeypatch.setenv("PLUGIN_FOLDER", "chickenbarncamera")
    monkeypatch.setenv("LBPLOG", str(log_dir))
    (mqtt_dir / "general.json").write_text(
        json.dumps({"mqtt": {"host": "loxberry-mqtt.local", "port": 1883}})
    )
    (bridge_dir / "smart-home-bridge.ini").write_text(
        "\n".join(
            [
                "[smart-home-bridge]",
                "MQTT_BASE_TOPIC=smart-home-bridge",
                "BRIDGE_DEVICES_ENABLED=chicken_thread_detector",
                "CAMERA_HOST=esp32cam.local",
                "LOG_FILE_PATH=logs/smart-home-bridge.log",
            ]
        )
        + "\n"
    )

    config = load_loxberry_config(home_dir, plugin_config_dir)

    assert config.devices.enabled == ("chicken_thread_detector",)
    assert config.camera.host == "esp32cam.local"
    assert config.log_file_path == str(
        log_dir / "chickenbarncamera" / "smart-home-bridge.log"
    )
