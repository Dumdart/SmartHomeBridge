from loxone_bridge.config import load_config


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
