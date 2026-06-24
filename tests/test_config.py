from smart_home_bridge.config import load_config


def test_load_config_reads_log_file_path(tmp_path):
    env_path = tmp_path / ".env"
    log_file_path = tmp_path / "bridge.log"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_BASE_URL=http://door.local",
                "DOOR_API_USERNAME=user",
                "DOOR_API_PASSWORD=password",
                "MQTT_HOST=mqtt.local",
                "MQTT_PORT=1883",
                "MQTT_USERNAME=user",
                "MQTT_PASSWORD=password",
                "MQTT_BASE_TOPIC=loxone",
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


def test_load_config_reads_independent_camera_and_threat_settings(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_BASE_URL=http://door.local",
                "DOOR_API_USERNAME=user",
                "DOOR_API_PASSWORD=password",
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
                "CHICKEN_THREAT_ENABLED=true",
                "CHICKEN_THREAT_MODEL_PATH=/models/chicken_threat_detector_best.pt",
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
    assert config.chicken_threat.enabled is True
    assert config.chicken_threat.model_path == "/models/chicken_threat_detector_best.pt"
    assert config.chicken_threat.poll_interval_seconds == 7.5


def test_load_config_disables_chicken_threat_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("CHICKEN_THREAT_ENABLED", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOOR_API_BASE_URL=http://door.local",
                "DOOR_API_USERNAME=user",
                "DOOR_API_PASSWORD=password",
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
