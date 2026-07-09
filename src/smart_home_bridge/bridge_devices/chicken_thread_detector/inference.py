import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from smart_home_contracts.chicken_thread import DetectionFrame


class ChickenThreatInferenceError(RuntimeError):
    pass


class ChickenThreatInferenceClient:
    def __init__(
        self,
        inference_url: str,
        timeout_seconds: float = 10.0,
    ):
        self.inference_url = inference_url
        self.timeout_seconds = timeout_seconds

    def detect(self, image_bytes: bytes, source: str | None = None) -> DetectionFrame:
        request = Request(
            self.inference_url,
            data=image_bytes,
            headers={"Content-Type": "image/jpeg"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ChickenThreatInferenceError(
                f"Inference backend rejected the frame with HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise ChickenThreatInferenceError(
                f"Inference backend is unavailable: {exc.reason}"
            ) from exc

        try:
            frame = DetectionFrame.from_mapping(json.loads(payload))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ChickenThreatInferenceError(
                "Inference backend returned an invalid detection frame."
            ) from exc

        if frame.source is None and source is not None:
            return DetectionFrame(detections=frame.detections, source=source)
        return frame


ChickenThreatInferenceService = ChickenThreatInferenceClient

__all__ = [
    "ChickenThreatInferenceClient",
    "ChickenThreatInferenceError",
    "ChickenThreatInferenceService",
]
