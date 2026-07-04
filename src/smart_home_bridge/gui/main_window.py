import asyncio

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.gui.factory import GuiBridgeContext, create_gui_bridge_context
from smart_home_bridge.gui.styles import APP_STYLESHEET
from smart_home_bridge.gui.widgets import (
    ActivityLogPanel,
    DiagnosticsPanel,
    DoorControlPanel,
    EnvironmentPanel,
    StatusStrip,
    ThreatDetectorPanel,
)


class MainWindow(QMainWindow):
    def __init__(self, context: GuiBridgeContext):
        super().__init__()
        self.context = context

        self.setWindowTitle("Smart Home Bridge")
        self.resize(1180, 820)
        self.setMinimumSize(920, 680)
        self.setStyleSheet(APP_STYLESHEET)

        self.status_strip = StatusStrip()
        self.door_panel = DoorControlPanel()
        self.threat_panel = ThreatDetectorPanel()
        self.diagnostics_panel = DiagnosticsPanel()
        self.environment_panel = EnvironmentPanel()
        self.activity_panel = ActivityLogPanel()

        self._wire_panels()
        self._build_layout()
        self._populate_settings_fields()
        self._refresh_status_labels()
        self._append_log("GUI started.")
        self._refresh_camera_health(log=True)

    def _wire_panels(self):
        self.door_panel.command_requested.connect(self._run_command)
        self.threat_panel.scan_requested.connect(self._run_threat_scan)
        self.threat_panel.health_requested.connect(
            lambda: self._refresh_camera_health(log=True)
        )
        self.environment_panel.save_requested.connect(self._save_environment_settings)

    def _build_layout(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self.status_strip)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 1)
        grid.setRowStretch(0, 3)

        grid.addWidget(self.door_panel, 0, 0)
        grid.addWidget(self.threat_panel, 0, 1)
        grid.addWidget(self.diagnostics_panel, 0, 2)
        grid.addWidget(self.environment_panel, 1, 0, 1, 3)
        grid.addWidget(self.activity_panel, 2, 0, 1, 3)
        layout.addLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def _run_command(self, command_name: str):
        self._set_status(f"Running {command_name}", "working")

        try:
            result = asyncio.run(
                self.context.door_controller.excecute_command(command_name)
            )
        except Exception as exc:
            self._set_status("Command failed", "danger")
            self._append_log(f"{command_name} failed: {exc}")
            return

        state = result.data
        if isinstance(state, door_position):
            self._set_door_state(state.value)

        self._set_status("Ready", "good")
        self._append_log(
            f"{command_name} completed with state {self.context.door.position.value}."
        )

    def _run_threat_scan(self):
        self._set_status("Running inference", "working")
        if not self._refresh_camera_health():
            self._append_log("Threat inference skipped because camera health check failed.")
            return
        self._set_status("Running inference", "working")

        try:
            result = asyncio.run(self.context.threat_scan_service.scan_once())
        except Exception as exc:
            self._set_status("Inference failed", "danger")
            self._append_log(f"Threat inference failed: {exc}")
            return

        self._refresh_threat_labels()
        self._render_inference_image(result.annotated_image_bytes)
        self._set_status("Ready", "good")
        self._append_log(
            "Threat inference completed with "
            f"{result.assessment.level.value} risk "
            f"from {result.assessment.detection_count} detections."
        )

    def _render_inference_image(self, image_bytes: bytes):
        self.threat_panel.render_image(image_bytes)

    def _append_log(self, message: str):
        entry = self.context.activity_log.record(message)
        self.activity_panel.append_entry(entry)

    def _populate_settings_fields(self):
        self.environment_panel.set_config(self.context.config)

    def _save_environment_settings(self):
        self._set_status("Saving settings", "working")

        try:
            config = self.context.env_settings.save_mqtt_http(
                mqtt=self.environment_panel.mqtt_config(),
                http=self.environment_panel.http_config(),
            )
        except Exception as exc:
            self._set_status("Save failed", "danger")
            self._append_log(f"Environment save failed: {exc}")
            return

        previous_state = self.context.door.position
        previous_assessment = self.context.threat_detector.assessment
        self.context = create_gui_bridge_context(config, self.context.env_settings)
        self.context.door.position = previous_state
        self.context.threat_detector.assessment = previous_assessment
        self._refresh_status_labels()
        camera_healthy = self._refresh_camera_health(log=True)
        if camera_healthy:
            self._set_status("Ready", "good")
        self._append_log("Environment settings saved.")

    def _refresh_status_labels(self):
        self._set_door_state(self.context.door.position.value)
        self.diagnostics_panel.set_details(
            mqtt_topic=self.context.command_topic,
            detector_topic=self.context.detector_topic,
            http_endpoint=self._http_endpoint(),
            camera_endpoint=self._camera_endpoint(),
        )
        self._refresh_threat_labels()

    def _refresh_camera_health(self, log: bool = False) -> bool:
        self._set_status("Checking camera", "working")
        is_healthy = self.context.threat_scan_service.camera_client.health()
        if is_healthy:
            self._set_camera_health("Available", "good")
            self._set_status("Ready", "good")
            if log:
                self._append_log(f"Camera health check passed: {self._camera_health_endpoint()}")
            return True

        self._set_camera_health("Unavailable", "danger")
        self._set_status("Camera unavailable", "danger")
        if log:
            self._append_log(f"Camera health check failed: {self._camera_health_endpoint()}")
        return False

    def _refresh_threat_labels(self):
        assessment = self.context.threat_detector.assessment
        tone = self._threat_tone(assessment.level.value)
        self.status_strip.set_threat(assessment.level.value, tone)
        self.threat_panel.set_assessment(
            assessment.level.value,
            assessment.score,
            assessment.detection_count,
            tone,
        )

    def _set_status(self, message: str, tone: str):
        self.status_strip.set_bridge(message, tone)

    def _set_door_state(self, value: str):
        tone = self._door_tone(value)
        self.status_strip.set_door(value, tone)
        self.door_panel.set_state(value, tone)

    def _set_camera_health(self, value: str, tone: str):
        self.status_strip.set_camera(value, tone)
        self.diagnostics_panel.set_camera_health(value, tone)

    def _door_tone(self, value: str) -> str:
        if value == door_position.OPEN.value:
            return "warning"
        if value == door_position.CLOSED.value:
            return "good"
        return "neutral"

    def _threat_tone(self, value: str) -> str:
        if value in {"critical", "high"}:
            return "danger"
        if value == "medium":
            return "warning"
        if value == "low":
            return "notice"
        return "good"

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.threat_panel.update_inference_pixmap()

    def _http_endpoint(self) -> str:
        return f"{self.context.config.http.host}:{self.context.config.http.port}"

    def _camera_endpoint(self) -> str:
        config = self.context.config.camera
        return f"{config.host}:{config.port}{config.jpg_endpoint}"

    def _camera_health_endpoint(self) -> str:
        config = self.context.config.camera
        return f"http://{config.host}:{config.port}/{config.health_endpoint.lstrip('/')}"
