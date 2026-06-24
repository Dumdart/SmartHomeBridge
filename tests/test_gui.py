import asyncio
from io import BytesIO
from pathlib import Path

from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.config import (
    CameraConfig,
    ChickenThreatConfig,
    DoorApiConfig,
    HttpConfig,
    MqttConfig,
    app_config,
)
from smart_home_bridge.core.command import command_result
from smart_home_bridge.gui import run
from smart_home_bridge.gui.factory import create_gui_bridge_context
from smart_home_bridge.gui.threat_detection import (
    GuiThreatScanService,
    annotate_detection_jpeg,
)
from smart_home_bridge.models import (
    BoundingBox,
    DangerAssessment,
    Detection,
    DetectionFrame,
    ThreatLevel,
)


def _config():
    return app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
        ),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="loxone",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        camera=CameraConfig(host="esp32cam.local", port=80, jpg_endpoint="/jpg"),
        chicken_threat=ChickenThreatConfig(
            enabled=True,
            model_path="/models/chicken_threat_detector_best.pt",
            poll_interval_seconds=7,
        ),
    )


def test_gui_entrypoint_imports_without_pyside6():
    assert callable(run)


def test_gui_context_wires_chicken_door_controller():
    context = create_gui_bridge_context(_config())

    assert context.door.position == door_position.UNKNOWN
    assert context.door_controller.device is context.door
    assert context.command_topic == "loxone/chicken-door"
    assert context.activity_log.log_file_path == Path("logs/loxone-bridge.log")


def test_gui_context_wires_chicken_threat_detector():
    context = create_gui_bridge_context(_config())

    assert context.threat_detector.name == "chicken_thread_detector"
    assert context.threat_detector_controller.detector is context.threat_detector
    assert context.detector_topic == "loxone/chicken-thread-detector"
    assert context.threat_scan_service.camera_client.config == context.config.camera
    assert (
        context.threat_scan_service.inference_service.detector.config.model_path
        == "/models/chicken_threat_detector_best.pt"
    )


def test_gui_context_controller_executes_commands():
    context = create_gui_bridge_context(_config())
    context.door.position = door_position.CLOSED

    result = asyncio.run(context.door_controller.excecute_command("open_door"))

    assert result.success is True
    assert context.door.position == door_position.OPEN


def test_gui_threat_scan_fetches_infers_scores_and_annotates_frame():
    frame = DetectionFrame(
        detections=(
            Detection(
                label="dog",
                confidence=0.9,
                box=BoundingBox(left=0.1, top=0.1, right=0.5, bottom=0.5),
            ),
        ),
        source="esp32cam.local",
    )
    assessment = DangerAssessment(
        level=ThreatLevel.MEDIUM,
        score=0.675,
        triggering_detections=frame.detections,
        detection_count=1,
    )
    controller = FakeThreatController(assessment)
    service = GuiThreatScanService(
        camera_client=FakeCameraClient(_jpeg_bytes()),
        inference_service=FakeInferenceService(frame),
        detector_controller=controller,
        source="esp32cam.local",
    )

    result = asyncio.run(service.scan_once())

    assert result.frame == frame
    assert result.assessment == assessment
    assert controller.frames == [frame]
    assert result.annotated_image_bytes.startswith(b"\xff\xd8")


def test_annotate_detection_jpeg_draws_detection_border():
    frame = DetectionFrame(
        detections=(
            Detection(
                label="dog",
                confidence=0.9,
                box=BoundingBox(left=0.1, top=0.1, right=0.5, bottom=0.5),
            ),
        ),
        source="esp32cam.local",
    )

    annotated = annotate_detection_jpeg(_jpeg_bytes(), frame)

    assert annotated.startswith(b"\xff\xd8")
    assert _has_colored_pixel(annotated) is True


class FakeCameraClient:
    def __init__(self, image_bytes):
        self.image_bytes = image_bytes

    def fetch_jpeg(self):
        return self.image_bytes

    def health(self):
        return True


class FakeInferenceService:
    def __init__(self, frame):
        self.frame = frame
        self.calls = []

    def detect(self, image_bytes, source=None):
        self.calls.append((image_bytes, source))
        return self.frame


class FakeThreatController:
    def __init__(self, assessment):
        self.assessment = assessment
        self.frames = []

    async def score_frame(self, frame):
        self.frames.append(frame)
        return command_result(data=self.assessment)


def _jpeg_bytes() -> bytes:
    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (100, 100), "white").save(output, format="JPEG")
    return output.getvalue()


def _has_colored_pixel(image_bytes: bytes) -> bool:
    from PIL import Image

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    pixels = image.load()
    for x in range(image.width):
        for y in range(image.height):
            red, green, blue = pixels[x, y]
            if red < 245 or green < 245 or blue < 245:
                return True

    return False
