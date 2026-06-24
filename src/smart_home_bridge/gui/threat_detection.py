from dataclasses import dataclass
from io import BytesIO

from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatInferenceService,
    chicken_thread_detector_controller,
)
from smart_home_bridge.infrastructure.camera import CameraClientInterface
from smart_home_bridge.models import BoundingBox, DangerAssessment, DetectionFrame


@dataclass(frozen=True)
class GuiThreatScanResult:
    image_bytes: bytes
    annotated_image_bytes: bytes
    frame: DetectionFrame
    assessment: DangerAssessment


class GuiThreatScanService:
    def __init__(
        self,
        camera_client: CameraClientInterface,
        inference_service: ChickenThreatInferenceService,
        detector_controller: chicken_thread_detector_controller,
        source: str | None = None,
    ):
        self.camera_client = camera_client
        self.inference_service = inference_service
        self.detector_controller = detector_controller
        self.source = source

    async def scan_once(self) -> GuiThreatScanResult:
        image_bytes = self.camera_client.fetch_jpeg()
        frame = self.inference_service.detect(image_bytes, source=self.source)
        result = await self.detector_controller.score_frame(frame)
        assessment = result.data

        if not isinstance(assessment, DangerAssessment):
            raise RuntimeError("Threat detector did not return a danger assessment.")

        return GuiThreatScanResult(
            image_bytes=image_bytes,
            annotated_image_bytes=annotate_detection_jpeg(image_bytes, frame),
            frame=frame,
            assessment=assessment,
        )


def annotate_detection_jpeg(image_bytes: bytes, frame: DetectionFrame) -> bytes:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Install Pillow to render detector image annotations.") from exc

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    for detection in frame.detections:
        if detection.box is None:
            continue

        left, top, right, bottom = _box_to_pixels(detection.box, width, height)
        label = f"{detection.label} {detection.confidence:.0%}"
        color = _color_for_confidence(detection.confidence)
        draw.rectangle((left, top, right, bottom), outline=color, width=3)
        label_box = draw.textbbox((left, top), label)
        label_height = label_box[3] - label_box[1]
        label_width = label_box[2] - label_box[0]
        label_top = max(0, top - label_height - 4)
        draw.rectangle(
            (left, label_top, left + label_width + 6, label_top + label_height + 4),
            fill=color,
        )
        draw.text((left + 3, label_top + 2), label, fill="white")

    output = BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()


def _box_to_pixels(
    box: BoundingBox,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    if box.normalized:
        left = round(box.left * image_width)
        top = round(box.top * image_height)
        right = round(box.right * image_width)
        bottom = round(box.bottom * image_height)
    else:
        left = round(box.left)
        top = round(box.top)
        right = round(box.right)
        bottom = round(box.bottom)

    left = max(0, min(image_width - 1, left))
    top = max(0, min(image_height - 1, top))
    right = max(0, min(image_width - 1, right))
    bottom = max(0, min(image_height - 1, bottom))

    left, right = sorted((left, right))
    top, bottom = sorted((top, bottom))
    return left, top, right, bottom


def _color_for_confidence(confidence: float) -> str:
    if confidence >= 0.8:
        return "#d92d20"
    if confidence >= 0.5:
        return "#f79009"
    return "#1570ef"
