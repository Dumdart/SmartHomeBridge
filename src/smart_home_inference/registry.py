from collections.abc import Iterable

from smart_home_inference.exceptions import ModelUnavailableError
from smart_home_inference.config import load_inference_config_from_environment
from smart_home_inference.models.base import InferenceModel
from smart_home_inference.models.chicken_thread.detector import LocalChickenThreadDetector
from smart_home_inference.models.chicken_thread.inference import ChickenThreatInferenceService


class ModelRegistry:
    def __init__(self, models: Iterable[InferenceModel]):
        self._models = {model.identifier: model for model in models}

    def identifiers(self) -> list[str]:
        return sorted(self._models)

    def get(self, identifier: str) -> InferenceModel:
        try:
            return self._models[identifier]
        except KeyError as exc:
            raise ModelUnavailableError(f"Unknown model: {identifier}") from exc


def default_model_registry() -> ModelRegistry:
    config = load_inference_config_from_environment()
    return ModelRegistry(
        [
            ChickenThreatInferenceService(
                detector=LocalChickenThreadDetector(config.chicken_threat)
            )
        ]
    )
