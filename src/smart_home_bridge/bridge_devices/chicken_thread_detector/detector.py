from typing import Any

from smart_home_bridge.bridge_devices.chicken_thread_detector.model_config import default_model_config
from smart_home_bridge.models import BoundingBox, ChickenThreadModelConfig, Detection, DetectionFrame


class LocalChickenThreadDetector:
    def __init__(self, config: ChickenThreadModelConfig | None = None, model: Any | None = None):
        self.config = config or default_model_config()
        self.model = model

    def detect(self, image: Any, source: str | None = None) -> DetectionFrame:
        model = self._model()
        results = model.predict(
            image,
            conf=self.config.confidence_threshold,
            imgsz=self.config.image_size,
            verbose=False,
        )

        if not results:
            return DetectionFrame(source=source)

        return DetectionFrame(
            detections=tuple(self._detections_from_result(results[0])),
            source=source,
        )

    def _model(self):
        if self.model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError(
                    "Install ultralytics to run the local chicken thread detector model."
                ) from exc

            self.model = YOLO(self.config.model_path)

        return self.model

    def _detections_from_result(self, result) -> list[Detection]:
        names = getattr(result, "names", {})
        detections = []

        for box in getattr(result, "boxes", []):
            class_id = int(box.cls.item())
            label = names.get(class_id, str(class_id))
            confidence = float(box.conf.item())
            left, top, right, bottom = [float(value) for value in box.xyxyn[0].tolist()]
            detections.append(
                Detection(
                    label=self.config.normalized_label(label),
                    confidence=confidence,
                    box=BoundingBox(left=left, top=top, right=right, bottom=bottom),
                )
            )

        return detections
