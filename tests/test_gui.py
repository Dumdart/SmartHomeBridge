import asyncio
from dataclasses import replace
from io import BytesIO
import os
from pathlib import Path

import pytest

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
from smart_home_bridge.bridge_devices.chicken_thread_detector.image_limits import (
    MAX_IMAGE_PIXELS,
)
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


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _config(log_file_path: str = "logs/smart-home-bridge.log"):
    return app_config(
        door_api=DoorApiConfig(
            api_key="api-key",
            device_id="device-id",
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
        log_file_path=log_file_path,
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
    assert context.command_topic == "loxone/chicken-door/command"
    assert context.activity_log.log_file_path == Path("logs/smart-home-bridge.log")


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
    context = create_gui_bridge_context(_config(), door_gateway_factory=lambda _: None)
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


def test_annotate_detection_jpeg_rejects_oversized_image(monkeypatch):
    from smart_home_bridge.gui import threat_detection

    def reject_image(_image):
        raise RuntimeError(f"Camera image exceeds {MAX_IMAGE_PIXELS} pixels: test")

    monkeypatch.setattr(threat_detection, "validate_image_size", reject_image)

    try:
        annotate_detection_jpeg(_jpeg_bytes(), DetectionFrame())
    except RuntimeError as exc:
        assert f"exceeds {MAX_IMAGE_PIXELS} pixels" in str(exc)
    else:
        raise AssertionError("Expected oversized GUI image to be rejected")


@pytest.fixture()
def qt_app():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    return app


def test_gui_panels_construct_without_device_clients(qt_app):
    from smart_home_bridge.gui.widgets import (
        ActivityLogPanel,
        DiagnosticsPanel,
        DoorControlPanel,
        EnvironmentPanel,
        StatusStrip,
        ThreatDetectorPanel,
    )

    assert StatusStrip().objectName() == "statusStrip"
    assert DoorControlPanel().objectName() == "operatorPanel"
    assert ThreatDetectorPanel().objectName() == "threatPanel"
    assert DiagnosticsPanel().objectName() == "diagnosticsPanel"
    assert EnvironmentPanel().objectName() == "environmentPanel"
    assert ActivityLogPanel().objectName() == "activityPanel"


def test_gui_door_panel_emits_command_names(qt_app):
    from PySide6.QtWidgets import QPushButton

    from smart_home_bridge.gui.widgets import DoorControlPanel

    panel = DoorControlPanel()
    commands = []
    panel.command_requested.connect(commands.append)

    for button in panel.findChildren(QPushButton):
        button.click()

    assert commands == ["open_door", "close_door", "stop_door", "get_door_state"]


def test_gui_environment_panel_populates_and_builds_configs(qt_app):
    from smart_home_bridge.gui.widgets import EnvironmentPanel

    panel = EnvironmentPanel()
    panel.set_config(_config())
    panel.mqtt_host_input.setText("mqtt.updated.local")
    panel.http_port_input.setValue(9000)

    assert panel.mqtt_config() == MqttConfig(
        host="mqtt.updated.local",
        port=8883,
        username="user",
        password="password",
        base_topic="loxone",
    )
    assert panel.http_config() == HttpConfig(host="localhost", port=9000)
    assert panel.mqtt_password_input.echoMode() == panel.mqtt_password_input.EchoMode.Password


def test_gui_status_and_tone_mapping_updates_panels(qt_app, tmp_path):
    from smart_home_bridge.gui.main_window import MainWindow

    context = _window_context(tmp_path)
    window = MainWindow(context)
    context.door.position = door_position.CLOSED

    window._refresh_status_labels()
    window._set_camera_health("Available", "good")

    assert window.status_strip.door_value.text() == "closed"
    assert window.status_strip.door_value.property("tone") == "good"
    assert window.door_panel.state_value.text() == "closed"
    assert window.diagnostics_panel.camera_health_value.text() == "Available"
    assert window.diagnostics_panel.camera_health_value.property("tone") == "good"


def test_gui_main_window_wires_door_commands(qt_app, tmp_path):
    from smart_home_bridge.gui.main_window import MainWindow

    context = _window_context(tmp_path)
    context.door.position = door_position.CLOSED
    window = MainWindow(context)

    window.door_panel.command_requested.emit("open_door")

    assert context.door.position == door_position.OPEN
    assert window.door_panel.state_value.text() == "open"
    assert window.status_strip.bridge_value.text() == "Ready"


def test_gui_main_window_save_environment_uses_panel_values(qt_app, tmp_path):
    from smart_home_bridge.gui.main_window import MainWindow

    env_settings = FakeEnvSettings()
    context = _window_context(tmp_path, env_settings=env_settings)
    window = MainWindow(context)
    window.environment_panel.mqtt_host_input.setText("mqtt.saved.local")
    window.environment_panel.http_port_input.setValue(9091)

    window.environment_panel.save_requested.emit()

    assert env_settings.saved_mqtt.host == "mqtt.saved.local"
    assert env_settings.saved_http.port == 9091
    assert window.diagnostics_panel.http_endpoint_value.text() == "localhost:9091"


def test_gui_threat_panel_renders_valid_and_invalid_images(qt_app):
    from smart_home_bridge.gui.widgets import ThreatDetectorPanel

    panel = ThreatDetectorPanel()

    assert panel.render_image(b"not an image") is False
    assert panel.image_label.text() == "Could not render inferred frame"
    assert panel.render_image(_jpeg_bytes()) is True
    assert panel.image_label.pixmap() is not None


class FakeCameraClient:
    def __init__(self, image_bytes):
        self.image_bytes = image_bytes

    def fetch_jpeg(self):
        return self.image_bytes

    def health(self):
        return True


class FakeEnvSettings:
    def __init__(self):
        self.saved_mqtt = None
        self.saved_http = None
        self.config = None

    def save_mqtt_http(self, mqtt, http):
        self.saved_mqtt = mqtt
        self.saved_http = http
        self.config = replace(self.config, mqtt=mqtt, http=http)
        return self.config


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


def _window_context(tmp_path, env_settings=None):
    config = _config(str(tmp_path / "smart-home-bridge.log"))
    if env_settings is not None:
        env_settings.config = config
    context = create_gui_bridge_context(
        config,
        env_settings=env_settings,
        door_gateway_factory=lambda _: None,
    )
    context.threat_scan_service.camera_client = FakeCameraClient(_jpeg_bytes())
    return context


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
