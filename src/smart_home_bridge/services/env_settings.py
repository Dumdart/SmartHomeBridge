from pathlib import Path

from smart_home_bridge.config import (
    BridgeDevicesConfig,
    CameraConfig,
    ChickenThreatConfig,
    HttpConfig,
    MqttConfig,
    app_config,
    load_config,
)


class EnvSettingsService:
    def __init__(self, env_path: str | Path = ".env"):
        self.env_path = Path(env_path)

    def load(self) -> app_config:
        return load_config(str(self.env_path), override=True)

    def save_mqtt_http(self, mqtt: MqttConfig, http: HttpConfig) -> app_config:
        values = {
            "MQTT_HOST": mqtt.host,
            "MQTT_PORT": str(_validate_port("MQTT_PORT", mqtt.port)),
            "MQTT_USERNAME": mqtt.username,
            "MQTT_PASSWORD": mqtt.password,
            "MQTT_BASE_TOPIC": mqtt.base_topic,
            "HTTP_HOST": http.host,
            "HTTP_PORT": str(_validate_port("HTTP_PORT", http.port)),
        }

        _write_env_values(self.env_path, values)
        return self.load()

    def save_critical_settings(
        self,
        mqtt: MqttConfig,
        devices: BridgeDevicesConfig,
        camera: CameraConfig,
        chicken_threat: ChickenThreatConfig,
        log_level: str,
    ) -> app_config:
        values = {
            "MQTT_HOST": mqtt.host,
            "MQTT_PORT": str(_validate_port("MQTT_PORT", mqtt.port)),
            "MQTT_USERNAME": mqtt.username,
            "MQTT_PASSWORD": mqtt.password,
            "MQTT_BASE_TOPIC": mqtt.base_topic,
            "MQTT_USE_TLS": _format_bool(mqtt.use_tls),
            "BRIDGE_DEVICES_ENABLED": ",".join(devices.enabled),
            "CAMERA_HOST": camera.host,
            "CAMERA_PORT": str(_validate_port("CAMERA_PORT", camera.port)),
            "CAMERA_JPG_ENDPOINT": camera.jpg_endpoint,
            "CAMERA_HEALTH_ENDPOINT": camera.health_endpoint,
            "CAMERA_TIMEOUT_SECONDS": str(camera.timeout_seconds),
            "CAMERA_MAX_JPEG_BYTES": str(camera.max_jpeg_bytes),
            "CAMERA_AUTH_TOKEN": camera.auth_token,
            "CHICKEN_THREAT_ENABLED": _format_bool(chicken_threat.enabled),
            "CHICKEN_THREAT_MODEL_PATH": chicken_threat.model_path,
            "CHICKEN_THREAT_POLL_INTERVAL_SECONDS": str(
                chicken_threat.poll_interval_seconds
            ),
            "LOG_LEVEL": log_level,
        }

        _write_env_values(self.env_path, values)
        return self.load()


def _validate_port(name: str, value: int) -> int:
    if value < 1 or value > 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return value


def _write_env_values(env_path: Path, values: dict[str, str]):
    existing_lines = env_path.read_text().splitlines() if env_path.exists() else []
    written_keys: set[str] = set()
    output_lines: list[str] = []

    for line in existing_lines:
        key = _env_key(line)
        if key in values:
            output_lines.append(f"{key}={_format_env_value(values[key])}")
            written_keys.add(key)
        else:
            output_lines.append(line)

    for key, value in values.items():
        if key not in written_keys:
            output_lines.append(f"{key}={_format_env_value(value)}")

    env_path.write_text("\n".join(output_lines) + "\n")


def _env_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def _format_env_value(value: str) -> str:
    if value == "" or any(character.isspace() for character in value) or "#" in value:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def _format_bool(value: bool) -> str:
    return "true" if value else "false"
