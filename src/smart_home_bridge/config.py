import os
from dataclasses import dataclass

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
class app_config:
    door_api: DoorApiConfig
    mqtt: MqttConfig
    http: HttpConfig
    log_level: str
    log_file_path: str = "logs/loxone-bridge.log"


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
        log_file_path=_get("LOG_FILE_PATH", "logs/loxone-bridge.log"),
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
