from collections.abc import Callable
from io import BytesIO
from typing import Any

from smart_home_contracts.chicken_thread import DetectionFrame
from smart_home_inference.exceptions import (
    ImageTooLargeError,
    InferenceExecutionError,
    InvalidImageError,
    ModelUnavailableError,
)
from smart_home_inference.models.chicken_thread.detector import LocalChickenThreadDetector
from smart_home_inference.models.chicken_thread.image_limits import validate_image_size


ImageDecoder = Callable[[bytes], Any]


class ChickenThreatInferenceService:
    identifier = "chicken-threat"

    def __init__(
        self,
        detector: LocalChickenThreadDetector | None = None,
        image_decoder: ImageDecoder | None = None,
    ):
        self.detector = detector or LocalChickenThreadDetector()
        self.image_decoder = image_decoder or _decode_jpeg

    def detect(self, image_bytes: bytes, source: str | None = None) -> DetectionFrame:
        image = self.image_decoder(image_bytes)
        return self.detector.detect(image, source=source)

    def infer(self, image_bytes: bytes, source: str | None = None) -> DetectionFrame:
        try:
            return self.detect(image_bytes, source=source)
        except (ImageTooLargeError, InvalidImageError, ModelUnavailableError):
            raise
        except RuntimeError as exc:
            message = str(exc).lower()
            if "install ultralytics" in message or "model" in message:
                raise ModelUnavailableError(str(exc)) from exc
            raise InferenceExecutionError(str(exc)) from exc
        except Exception as exc:
            raise InferenceExecutionError(str(exc)) from exc

    def ready(self) -> tuple[bool, str | None]:
        if hasattr(self.detector, "ready"):
            return self.detector.ready()

        try:
            self.detector.detect(None)
        except Exception as exc:
            return False, str(exc)

        return True, None


def _decode_jpeg(image_bytes: bytes) -> Any:
    try:
        from PIL import Image
        from PIL import UnidentifiedImageError
    except ImportError as exc:
        raise ModelUnavailableError("Install Pillow to decode JPEG frames.") from exc

    try:
        image = Image.open(BytesIO(image_bytes))
        if image.format != "JPEG":
            raise InvalidImageError("Image payload must be a JPEG image.")
        validate_image_size(image)
        image.load()
        return image
    except (OSError, UnidentifiedImageError) as exc:
        raise InvalidImageError("Image payload is not a valid JPEG image.") from exc
