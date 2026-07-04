import json
import os
import re
from collections.abc import Mapping
from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class DoorApiConfig:
    api_key: str = field(repr=False)
    device_id: str


@dataclass(frozen=True)
class MqttConfig:
    host: str
    port: int
    username: str
    password: str
    base_topic: str
    use_tls: bool = False


@dataclass(frozen=True)
class HttpConfig:
    host: str
    port: int


@dataclass(frozen=True)
class CameraConfig:
    host: str = "192.168.1.42"
    port: int = 80
    jpg_endpoint: str = "/jpg"
    health_endpoint: str = "/health"
    timeout_seconds: float = 5.0
    max_jpeg_bytes: int = 2_000_000
    auth_token: str = field(default="", repr=False)


@dataclass(frozen=True)
class ChickenThreatConfig:
    enabled: bool = False
    model_path: str = "src/smart_home_bridge/models/chicken_threat_detector_best.pt"
    poll_interval_seconds: float = 10.0


@dataclass(frozen=True)
class BridgeDeviceConfig:
    key: str
    enabled: bool = True
    device_id: int | None = None
    name: str | None = None
    topics: dict[str, str] = field(default_factory=dict)

    def topic(self, name: str, default: str) -> str:
        return self.topics.get(name, default)


@dataclass(frozen=True)
class BridgeDevicesConfig:
    enabled: tuple[str, ...] = ("chicken_door", "chicken_thread_detector")
    configs: dict[str, BridgeDeviceConfig] = field(default_factory=dict)

    def is_enabled(self, key: str) -> bool:
        device_config = self.configs.get(key)
        if device_config is not None:
            return device_config.enabled and key in self.enabled
        return key in self.enabled

    def for_device(self, key: str) -> BridgeDeviceConfig:
        device_config = self.configs.get(key)
        if device_config is not None:
            return device_config
        return BridgeDeviceConfig(key=key, enabled=key in self.enabled)


@dataclass(frozen=True)
class app_config:
    door_api: DoorApiConfig
    mqtt: MqttConfig
    http: HttpConfig
    log_level: str
    log_file_path: str = "logs/smart-home-bridge.log"
    camera: CameraConfig = field(default_factory=CameraConfig)
    chicken_threat: ChickenThreatConfig = field(default_factory=ChickenThreatConfig)
    devices: BridgeDevicesConfig = field(default_factory=BridgeDevicesConfig)


def load_config(dotenv_path: str | None = None, override: bool = False) -> app_config:
    load_dotenv(dotenv_path=dotenv_path, override=override)
    return _config_from_mapping(os.environ, require_mqtt_credentials=True)


def load_loxberry_config(
    home_dir: str | Path | None = None,
    plugin_config_dir: str | Path | None = None,
) -> app_config:
    loxberry_home = Path(home_dir or _required_env("LBHOMEDIR"))
    loxberry_plugin_config = Path(plugin_config_dir or _required_env("LBPCONFIG"))
    mqtt_config_path = loxberry_home / "config" / "system" / "general.json"
    bridge_config_path = (
        loxberry_plugin_config / "smarthomebridge" / "smart-home-bridge.ini"
    )

    mqtt_settings = _read_loxberry_mqtt_settings(mqtt_config_path)
    bridge_settings = _read_ini_settings(bridge_config_path)
    values = {**bridge_settings, **mqtt_settings}
    return _config_from_mapping(values, require_mqtt_credentials=False)


def _config_from_mapping(
    values: Mapping[str, str],
    require_mqtt_credentials: bool = True,
) -> app_config:
    return app_config(
        door_api=DoorApiConfig(
            api_key=_required(values, "DOOR_API_KEY"),
            device_id=_required(values, "DOOR_DEVICE_ID"),
        ),
        mqtt=MqttConfig(
            host=_required(values, "MQTT_HOST"),
            port=_int(values, "MQTT_PORT", 1883),
            username=_mqtt_credential(values, "MQTT_USERNAME", require_mqtt_credentials),
            password=_mqtt_credential(values, "MQTT_PASSWORD", require_mqtt_credentials),
            base_topic=_required(values, "MQTT_BASE_TOPIC"),
            use_tls=_bool(values, "MQTT_USE_TLS", False),
        ),
        http=HttpConfig(
            host=_get(values, "HTTP_HOST", "0.0.0.0"),
            port=_int(values, "HTTP_PORT", 8080),
        ),
        log_level=_get(values, "LOG_LEVEL", "INFO"),
        log_file_path=_get(values, "LOG_FILE_PATH", "logs/smart-home-bridge.log"),
        camera=CameraConfig(
            host=_get(values, "CAMERA_HOST", "192.168.1.42"),
            port=_int(values, "CAMERA_PORT", 80),
            jpg_endpoint=_get(values, "CAMERA_JPG_ENDPOINT", "/jpg"),
            health_endpoint=_get(values, "CAMERA_HEALTH_ENDPOINT", "/health"),
            timeout_seconds=_float(values, "CAMERA_TIMEOUT_SECONDS", 5.0),
            max_jpeg_bytes=_int(values, "CAMERA_MAX_JPEG_BYTES", 2_000_000),
            auth_token=_get(values, "CAMERA_AUTH_TOKEN", ""),
        ),
        chicken_threat=ChickenThreatConfig(
            enabled=_bool(values, "CHICKEN_THREAT_ENABLED", False),
            model_path=_get(
                values,
                "CHICKEN_THREAT_MODEL_PATH",
                "src/smart_home_bridge/models/chicken_threat_detector_best.pt",
            ),
            poll_interval_seconds=_float(
                values,
                "CHICKEN_THREAT_POLL_INTERVAL_SECONDS",
                10.0,
            ),
        ),
        devices=_bridge_devices_config(values),
    )


def _get(values: Mapping[str, str], name: str, default: str) -> str:
    value = values.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _mqtt_credential(
    values: Mapping[str, str],
    name: str,
    required: bool,
) -> str:
    if required:
        return _required(values, name)
    return _get(values, name, "")


def _int(values: Mapping[str, str], name: str, default: int) -> int:
    value = _get(values, name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _float(values: Mapping[str, str], name: str, default: float) -> float:
    value = _get(values, name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number") from exc


def _bool(values: Mapping[str, str], name: str, default: bool) -> bool:
    value = values.get(name)
    if value is None or value.strip() == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Environment variable {name} must be a boolean")


def _csv(values: Mapping[str, str], name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = values.get(name)
    if value is None or value.strip() == "":
        return default

    return tuple(part.strip() for part in value.split(",") if part.strip())


def _optional_int(
    values: Mapping[str, str],
    name: str,
    default: int | None = None,
) -> int | None:
    value = values.get(name)
    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _bridge_devices_config(values: Mapping[str, str]) -> BridgeDevicesConfig:
    enabled = _csv(
        values,
        "BRIDGE_DEVICES_ENABLED",
        ("chicken_door", "chicken_thread_detector"),
    )
    return BridgeDevicesConfig(
        enabled=enabled,
        configs={
            "chicken_door": BridgeDeviceConfig(
                key="chicken_door",
                enabled="chicken_door" in enabled,
                device_id=_optional_int(values, "CHICKEN_DOOR_BRIDGE_ID", 1),
                name=_get(values, "CHICKEN_DOOR_BRIDGE_NAME", "door"),
                topics={
                    "command": _get(
                        values,
                        "CHICKEN_DOOR_COMMAND_TOPIC",
                        "chicken-door/command",
                    ),
                    "status": _get(
                        values,
                        "CHICKEN_DOOR_STATUS_TOPIC",
                        "chicken-door/status",
                    ),
                    "status_code": _get(
                        values,
                        "CHICKEN_DOOR_STATUS_CODE_TOPIC",
                        "chicken-door/status_code",
                    ),
                    "fault": _get(
                        values,
                        "CHICKEN_DOOR_FAULT_TOPIC",
                        "chicken-door/fault",
                    ),
                    "connected": _get(
                        values,
                        "CHICKEN_DOOR_CONNECTED_TOPIC",
                        "chicken-door/connected",
                    ),
                    "battery": _get(
                        values,
                        "CHICKEN_DOOR_BATTERY_TOPIC",
                        "chicken-door/battery",
                    ),
                    "light_level": _get(
                        values,
                        "CHICKEN_DOOR_LIGHT_LEVEL_TOPIC",
                        "chicken-door/light_level",
                    ),
                },
            ),
            "chicken_thread_detector": BridgeDeviceConfig(
                key="chicken_thread_detector",
                enabled="chicken_thread_detector" in enabled,
                device_id=_optional_int(
                    values,
                    "CHICKEN_THREAD_DETECTOR_BRIDGE_ID",
                    2,
                ),
                name=_get(
                    values,
                    "CHICKEN_THREAD_DETECTOR_BRIDGE_NAME",
                    "chicken_thread_detector",
                ),
                topics={
                    "detections": _get(
                        values,
                        "CHICKEN_THREAD_DETECTOR_TOPIC",
                        "chicken-thread-detector",
                    ),
                },
            ),
        },
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _read_ini_settings(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ValueError(f"Missing LoxBerry bridge config file: {path}")

    parser = ConfigParser()
    parser.optionxform = str
    parser.read(path)
    settings: dict[str, str] = {}
    for section in parser.sections():
        for key, value in parser.items(section):
            settings[key.upper()] = value.strip()
    return settings


def _read_loxberry_mqtt_settings(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ValueError(f"Missing LoxBerry MQTT config file: {path}")

    data = json.loads(path.read_text())
    flattened = _flatten_json_keys(data)
    return {
        "MQTT_HOST": _first(
            flattened,
            "mqtthost",
            "mqttbrokerhost",
            "brokerhost",
            "host",
        ),
        "MQTT_PORT": _first(flattened, "mqttport", "mqttbrokerport", "brokerport", "port"),
        "MQTT_USERNAME": _first(
            flattened,
            "mqttusername",
            "mqttuser",
            "mqttbrokeruser",
            "brokeruser",
            "username",
            "user",
            default="",
        ),
        "MQTT_PASSWORD": _first(
            flattened,
            "mqttpassword",
            "mqttpass",
            "mqttbrokerpass",
            "brokerpass",
            "password",
            "pass",
            default="",
        ),
        "MQTT_USE_TLS": _first(flattened, "mqttusetls", "mqtttls", "usetls", default="false"),
    }


def _flatten_json_keys(value, prefix: str = "") -> dict[str, str]:
    items: dict[str, str] = {}
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(str(key))
            combined_key = f"{prefix}{normalized_key}" if prefix else normalized_key
            items.update(_flatten_json_keys(nested_value, combined_key))
            items.setdefault(normalized_key, _scalar_to_str(nested_value))
    return items


def _first(values: Mapping[str, str], *names: str, default: str | None = None) -> str:
    for name in names:
        value = values.get(_normalize_key(name))
        if value is not None and value.strip() != "":
            return value.strip()
    if default is not None:
        return default
    raise ValueError(f"Missing LoxBerry MQTT setting: {' or '.join(names)}")


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _scalar_to_str(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float | str):
        return str(value)
    return ""
