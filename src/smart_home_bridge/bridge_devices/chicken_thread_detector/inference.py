from collections.abc import Callable
from io import BytesIO
from typing import Any

from smart_home_bridge.bridge_devices.chicken_thread_detector.detector import (
    LocalChickenThreadDetector,
)
from smart_home_bridge.models import DetectionFrame


ImageDecoder = Callable[[bytes], Any]


class ChickenThreatInferenceService:
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


def _decode_jpeg(image_bytes: bytes) -> Any:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install Pillow to decode camera JPEG frames.") from exc

    image = Image.open(BytesIO(image_bytes))
    image.load()
    return image
