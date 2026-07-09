import os
from collections.abc import Mapping
from dataclasses import dataclass

from smart_home_inference.models.chicken_thread.config import (
    DEFAULT_CHICKEN_THREAT_MODEL_PATH,
    LABEL_ALIASES,
    MODEL_CLASS_NAMES,
    RISK_BY_LABEL,
    ChickenThreadModelConfig,
    default_model_config,
)


@dataclass(frozen=True)
class InferenceHttpConfig:
    host: str = "0.0.0.0"
    port: int = 8090


@dataclass(frozen=True)
class InferenceConfig:
    http: InferenceHttpConfig
    chicken_threat: ChickenThreadModelConfig


def load_inference_config_from_environment() -> InferenceConfig:
    return inference_config_from_mapping(os.environ)


def inference_config_from_mapping(values: Mapping[str, str]) -> InferenceConfig:
    return InferenceConfig(
        http=InferenceHttpConfig(
            host=_get(values, "INFERENCE_HTTP_HOST", "0.0.0.0"),
            port=_int(values, "INFERENCE_HTTP_PORT", 8090),
        ),
        chicken_threat=default_model_config(
            model_path=_get(
                values,
                "CHICKEN_THREAT_MODEL_PATH",
                DEFAULT_CHICKEN_THREAT_MODEL_PATH,
            ),
            confidence_threshold=_float(
                values,
                "CHICKEN_THREAT_CONFIDENCE_THRESHOLD",
                0.35,
            ),
            image_size=_int(values, "CHICKEN_THREAT_IMAGE_SIZE", 640),
        ),
    )


def _get(values: Mapping[str, str], name: str, default: str) -> str:
    value = values.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


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

__all__ = [
    "DEFAULT_CHICKEN_THREAT_MODEL_PATH",
    "LABEL_ALIASES",
    "MODEL_CLASS_NAMES",
    "RISK_BY_LABEL",
    "ChickenThreadModelConfig",
    "InferenceConfig",
    "InferenceHttpConfig",
    "default_model_config",
    "inference_config_from_mapping",
    "load_inference_config_from_environment",
]
