import os
from dataclasses import dataclass, field

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

    return app_config(
        door_api=DoorApiConfig(
            api_key=_required("DOOR_API_KEY"),
            device_id=_required("DOOR_DEVICE_ID"),
        ),
        mqtt=MqttConfig(
            host=_required("MQTT_HOST"),
            port=_int("MQTT_PORT", 1883),
            username=_required("MQTT_USERNAME"),
            password=_required("MQTT_PASSWORD"),
            base_topic=_required("MQTT_BASE_TOPIC"),
            use_tls=_bool("MQTT_USE_TLS", False),
        ),
        http=HttpConfig(
            host=_get("HTTP_HOST", "0.0.0.0"),
            port=_int("HTTP_PORT", 8080),
        ),
        log_level=_get("LOG_LEVEL", "INFO"),
        log_file_path=_get("LOG_FILE_PATH", "logs/smart-home-bridge.log"),
        camera=CameraConfig(
            host=_get("CAMERA_HOST", "192.168.1.42"),
            port=_int("CAMERA_PORT", 80),
            jpg_endpoint=_get("CAMERA_JPG_ENDPOINT", "/jpg"),
            health_endpoint=_get("CAMERA_HEALTH_ENDPOINT", "/health"),
            timeout_seconds=_float("CAMERA_TIMEOUT_SECONDS", 5.0),
            max_jpeg_bytes=_int("CAMERA_MAX_JPEG_BYTES", 2_000_000),
            auth_token=_get("CAMERA_AUTH_TOKEN", ""),
        ),
        chicken_threat=ChickenThreatConfig(
            enabled=_bool("CHICKEN_THREAT_ENABLED", False),
            model_path=_get(
                "CHICKEN_THREAT_MODEL_PATH",
                "src/smart_home_bridge/models/chicken_threat_detector_best.pt",
            ),
            poll_interval_seconds=_float("CHICKEN_THREAT_POLL_INTERVAL_SECONDS", 10.0),
        ),
        devices=_bridge_devices_config(),
    )


def _get(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _int(name: str, default: int) -> int:
    value = _get(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _float(name: str, default: float) -> float:
    value = _get(name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number") from exc


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Environment variable {name} must be a boolean")


def _csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    return tuple(part.strip() for part in value.split(",") if part.strip())


def _optional_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _bridge_devices_config() -> BridgeDevicesConfig:
    enabled = _csv(
        "BRIDGE_DEVICES_ENABLED",
        ("chicken_door", "chicken_thread_detector"),
    )
    return BridgeDevicesConfig(
        enabled=enabled,
        configs={
            "chicken_door": BridgeDeviceConfig(
                key="chicken_door",
                enabled="chicken_door" in enabled,
                device_id=_optional_int("CHICKEN_DOOR_BRIDGE_ID", 1),
                name=_get("CHICKEN_DOOR_BRIDGE_NAME", "door"),
                topics={
                    "command": _get(
                        "CHICKEN_DOOR_COMMAND_TOPIC",
                        "chicken-door/command",
                    ),
                    "status": _get("CHICKEN_DOOR_STATUS_TOPIC", "chicken-door/status"),
                    "status_code": _get(
                        "CHICKEN_DOOR_STATUS_CODE_TOPIC",
                        "chicken-door/status_code",
                    ),
                    "fault": _get("CHICKEN_DOOR_FAULT_TOPIC", "chicken-door/fault"),
                    "connected": _get(
                        "CHICKEN_DOOR_CONNECTED_TOPIC",
                        "chicken-door/connected",
                    ),
                    "battery": _get(
                        "CHICKEN_DOOR_BATTERY_TOPIC",
                        "chicken-door/battery",
                    ),
                    "light_level": _get(
                        "CHICKEN_DOOR_LIGHT_LEVEL_TOPIC",
                        "chicken-door/light_level",
                    ),
                },
            ),
            "chicken_thread_detector": BridgeDeviceConfig(
                key="chicken_thread_detector",
                enabled="chicken_thread_detector" in enabled,
                device_id=_optional_int("CHICKEN_THREAD_DETECTOR_BRIDGE_ID", 2),
                name=_get(
                    "CHICKEN_THREAD_DETECTOR_BRIDGE_NAME",
                    "chicken_thread_detector",
                ),
                topics={
                    "detections": _get(
                        "CHICKEN_THREAD_DETECTOR_TOPIC",
                        "chicken-thread-detector",
                    ),
                },
            ),
        },
    )
