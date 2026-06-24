import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class DoorApiConfig:
    base_url: str
    username: str
    password: str


@dataclass(frozen=True)
class MqttConfig:
    host: str
    port: int
    username: str
    password: str
    base_topic: str


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


@dataclass(frozen=True)
class ChickenThreatConfig:
    enabled: bool = False
    model_path: str = "src/smart_home_bridge/models/chicken_threat_detector_best.pt"
    poll_interval_seconds: float = 10.0


@dataclass(frozen=True)
class app_config:
    door_api: DoorApiConfig
    mqtt: MqttConfig
    http: HttpConfig
    log_level: str
    log_file_path: str = "logs/smart-home-bridge.log"
    camera: CameraConfig = field(default_factory=CameraConfig)
    chicken_threat: ChickenThreatConfig = field(default_factory=ChickenThreatConfig)


def load_config(dotenv_path: str | None = None, override: bool = False) -> app_config:
    load_dotenv(dotenv_path=dotenv_path, override=override)

    return app_config(
        door_api=DoorApiConfig(
            base_url=_required("DOOR_API_BASE_URL"),
            username=_required("DOOR_API_USERNAME"),
            password=_required("DOOR_API_PASSWORD"),
        ),
        mqtt=MqttConfig(
            host=_required("MQTT_HOST"),
            port=_int("MQTT_PORT", 1883),
            username=_required("MQTT_USERNAME"),
            password=_required("MQTT_PASSWORD"),
            base_topic=_required("MQTT_BASE_TOPIC"),
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
        ),
        chicken_threat=ChickenThreatConfig(
            enabled=_bool("CHICKEN_THREAT_ENABLED", False),
            model_path=_get(
                "CHICKEN_THREAT_MODEL_PATH",
                "src/smart_home_bridge/models/chicken_threat_detector_best.pt",
            ),
            poll_interval_seconds=_float("CHICKEN_THREAT_POLL_INTERVAL_SECONDS", 10.0),
        ),
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
