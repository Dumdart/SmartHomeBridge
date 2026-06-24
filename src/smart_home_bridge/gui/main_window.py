import asyncio

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.config import HttpConfig, MqttConfig
from smart_home_bridge.gui.factory import GuiBridgeContext, create_gui_bridge_context


class MainWindow(QMainWindow):
    def __init__(self, context: GuiBridgeContext):
        super().__init__()
        self.context = context

        self.setWindowTitle("Smart Home Bridge")
        self.resize(920, 760)
        self.setMinimumSize(720, 620)
        self.setStyleSheet(APP_STYLESHEET)

        self.state_value = QLabel(self.context.door.position.value)
        self.state_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_value.setObjectName("doorStateValue")
        self.state_value.setProperty("tone", "neutral")

        self.mqtt_topic_value = QLabel(self.context.command_topic)
        self.detector_topic_value = QLabel(self.context.detector_topic)
        self.http_endpoint_value = QLabel(self._http_endpoint())
        self.camera_endpoint_value = QLabel(self._camera_endpoint())
        self.threat_level_value = QLabel(self.context.threat_detector.assessment.level.value)
        self.threat_level_value.setObjectName("threatLevelValue")
        self.threat_level_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threat_level_value.setProperty("tone", "good")
        self.threat_score_value = QLabel(f"{self.context.threat_detector.assessment.score:.4f}")
        self.threat_score_bar = QProgressBar()
        self.threat_score_bar.setRange(0, 10000)
        self.threat_score_bar.setTextVisible(False)
        self.threat_count_value = QLabel(
            str(self.context.threat_detector.assessment.detection_count)
        )
        self.status_value = QLabel("Ready")
        self.status_value.setObjectName("statusValue")
        self.status_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_value.setProperty("tone", "good")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(112)
        self.log_output.setObjectName("activityLog")
        self.inference_image_label = QLabel("No inferred frame")
        self.inference_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inference_image_label.setMinimumSize(480, 300)
        self.inference_image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.inference_image_label.setScaledContents(False)
        self.inference_image_label.setObjectName("inferenceImage")
        self._inference_pixmap = QPixmap()

        self.mqtt_host_input = QLineEdit()
        self.mqtt_port_input = QSpinBox()
        self.mqtt_port_input.setRange(1, 65535)
        self.mqtt_username_input = QLineEdit()
        self.mqtt_password_input = QLineEdit()
        self.mqtt_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mqtt_base_topic_input = QLineEdit()
        self.http_host_input = QLineEdit()
        self.http_port_input = QSpinBox()
        self.http_port_input.setRange(1, 65535)

        self._build_layout()
        self._populate_settings_fields()
        self._refresh_status_labels()
        self._append_log("GUI started.")

    def _build_layout(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_status_group())
        layout.addWidget(self._build_settings_group())
        layout.addWidget(self._build_command_group())
        layout.addWidget(self._build_detector_group())
        layout.addWidget(self._build_log_group())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        title = QLabel("Smart Home Bridge")
        title.setObjectName("appTitle")
        subtitle = QLabel("Local bridge control for chicken door, MQTT, diagnostics, and threat scans.")
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block, 1)

        layout.addWidget(self._build_metric_card("Door", self.state_value))
        layout.addWidget(self._build_metric_card("Threat", self.threat_level_value))
        layout.addWidget(self._build_metric_card("Bridge", self.status_value))

        return header

    def _build_metric_card(self, label: str, value: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumWidth(128)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        label_widget = QLabel(label)
        label_widget.setObjectName("metricLabel")

        layout.addWidget(label_widget)
        layout.addWidget(value)
        return card

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("Bridge Details")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        self._add_detail_row(layout, 0, 0, "MQTT topic", self.mqtt_topic_value)
        self._add_detail_row(layout, 1, 0, "Detector topic", self.detector_topic_value)
        self._add_detail_row(layout, 2, 0, "HTTP diagnostics", self.http_endpoint_value)
        self._add_detail_row(layout, 3, 0, "Camera endpoint", self.camera_endpoint_value)
        self._add_detail_row(layout, 0, 2, "Detector score", self.threat_score_value)
        layout.addWidget(self.threat_score_bar, 1, 3)
        self._add_detail_row(layout, 2, 2, "Detector count", self.threat_count_value)

        return group

    def _add_detail_row(
        self,
        layout: QGridLayout,
        row: int,
        column: int,
        label: str,
        value: QLabel,
    ):
        label_widget = QLabel(label)
        label_widget.setObjectName("detailLabel")
        value.setObjectName(value.objectName() or "detailValue")
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value.setWordWrap(True)

        layout.addWidget(label_widget, row, column)
        layout.addWidget(value, row, column + 1)

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("Connection Settings")
        layout = QFormLayout(group)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(10)

        layout.addRow("MQTT host", self.mqtt_host_input)
        layout.addRow("MQTT port", self.mqtt_port_input)
        layout.addRow("MQTT username", self.mqtt_username_input)
        layout.addRow("MQTT password", self.mqtt_password_input)
        layout.addRow("MQTT base topic", self.mqtt_base_topic_input)
        layout.addRow("HTTP host", self.http_host_input)
        layout.addRow("HTTP port", self.http_port_input)

        save_button = QPushButton("Save Environment")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save_environment_settings)
        layout.addRow(save_button)

        return group

    def _build_command_group(self) -> QGroupBox:
        group = QGroupBox("Chicken Door")
        layout = QHBoxLayout(group)

        commands = [
            ("Open Door", "open_door", "primaryButton"),
            ("Close Door", "close_door", "warningButton"),
            ("Stop", "stop_door", "dangerButton"),
            ("Refresh State", "get_door_state", ""),
        ]

        for label, command_name, object_name in commands:
            button = QPushButton(label)
            if object_name:
                button.setObjectName(object_name)
            button.clicked.connect(
                lambda _checked=False, name=command_name: self._run_command(name)
            )
            layout.addWidget(button)

        return group

    def _build_detector_group(self) -> QGroupBox:
        group = QGroupBox("Chicken Threat Detector")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        button_row = QHBoxLayout()
        scan_button = QPushButton("Run Inference")
        scan_button.setObjectName("primaryButton")
        scan_button.clicked.connect(self._run_threat_scan)
        button_row.addWidget(scan_button)
        button_row.addStretch(1)

        caption = QLabel("Latest annotated camera frame")
        caption.setObjectName("sectionCaption")

        layout.addLayout(button_row)
        layout.addWidget(caption)
        layout.addWidget(self.inference_image_label)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Activity")
        layout = QVBoxLayout(group)
        layout.addWidget(self.log_output)
        return group

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
            self.state_value.setText(state.value)
            self._set_badge_tone(self.state_value, self._door_tone(state.value))

        self._set_status("Ready", "good")
        self._append_log(
            f"{command_name} completed with state {self.context.door.position.value}."
        )

    def _run_threat_scan(self):
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
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_bytes):
            self.inference_image_label.setText("Could not render inferred frame")
            self._inference_pixmap = QPixmap()
            self.inference_image_label.setPixmap(QPixmap())
            return

        self._inference_pixmap = pixmap
        self._update_inference_pixmap()

    def _append_log(self, message: str):
        entry = self.context.activity_log.record(message)
        self.log_output.append(entry)

    def _populate_settings_fields(self):
        self.mqtt_host_input.setText(self.context.config.mqtt.host)
        self.mqtt_port_input.setValue(self.context.config.mqtt.port)
        self.mqtt_username_input.setText(self.context.config.mqtt.username)
        self.mqtt_password_input.setText(self.context.config.mqtt.password)
        self.mqtt_base_topic_input.setText(self.context.config.mqtt.base_topic)
        self.http_host_input.setText(self.context.config.http.host)
        self.http_port_input.setValue(self.context.config.http.port)

    def _save_environment_settings(self):
        self._set_status("Saving settings", "working")

        try:
            config = self.context.env_settings.save_mqtt_http(
                mqtt=MqttConfig(
                    host=self.mqtt_host_input.text().strip(),
                    port=self.mqtt_port_input.value(),
                    username=self.mqtt_username_input.text().strip(),
                    password=self.mqtt_password_input.text(),
                    base_topic=self.mqtt_base_topic_input.text().strip(),
                ),
                http=HttpConfig(
                    host=self.http_host_input.text().strip(),
                    port=self.http_port_input.value(),
                ),
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

        self._set_status("Ready", "good")
        self._append_log("Environment settings saved.")

    def _refresh_status_labels(self):
        self.state_value.setText(self.context.door.position.value)
        self._set_badge_tone(
            self.state_value,
            self._door_tone(self.context.door.position.value),
        )
        self.mqtt_topic_value.setText(self.context.command_topic)
        self.detector_topic_value.setText(self.context.detector_topic)
        self.http_endpoint_value.setText(self._http_endpoint())
        self.camera_endpoint_value.setText(self._camera_endpoint())
        self._refresh_threat_labels()

    def _refresh_threat_labels(self):
        assessment = self.context.threat_detector.assessment
        self.threat_level_value.setText(assessment.level.value)
        self._set_badge_tone(self.threat_level_value, self._threat_tone(assessment.level.value))
        self.threat_score_value.setText(f"{assessment.score:.4f}")
        self.threat_score_bar.setValue(max(0, min(10000, int(assessment.score * 10000))))
        self.threat_count_value.setText(str(assessment.detection_count))

    def _set_status(self, message: str, tone: str):
        self.status_value.setText(message)
        self._set_badge_tone(self.status_value, tone)

    def _set_badge_tone(self, widget: QLabel, tone: str):
        widget.setProperty("tone", tone)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

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

    def _update_inference_pixmap(self):
        if self._inference_pixmap.isNull():
            return

        scaled = self._inference_pixmap.scaled(
            self.inference_image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.inference_image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_inference_pixmap()

    def _http_endpoint(self) -> str:
        return f"{self.context.config.http.host}:{self.context.config.http.port}"

    def _camera_endpoint(self) -> str:
        config = self.context.config.camera
        return f"{config.host}:{config.port}{config.jpg_endpoint}"


APP_STYLESHEET = """
QMainWindow,
QScrollArea,
QWidget {
    background: #111827;
    color: #e5e7eb;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QFrame#appHeader {
    background: #172033;
    border: 1px solid #263348;
    border-radius: 8px;
}

QLabel#appTitle {
    color: #f9fafb;
    font-size: 22px;
    font-weight: 700;
}

QLabel#appSubtitle,
QLabel#sectionCaption {
    color: #9ca3af;
}

QFrame#metricCard {
    background: #0f172a;
    border: 1px solid #2f3b52;
    border-radius: 8px;
}

QLabel#metricLabel,
QLabel#detailLabel {
    color: #9ca3af;
    font-size: 12px;
    font-weight: 600;
}

QLabel#detailValue {
    color: #f3f4f6;
}

QLabel#doorStateValue,
QLabel#threatLevelValue,
QLabel#statusValue {
    border-radius: 6px;
    font-weight: 700;
    padding: 6px 10px;
}

QLabel[tone="good"] {
    background: #113f2c;
    color: #bbf7d0;
}

QLabel[tone="notice"] {
    background: #173554;
    color: #bfdbfe;
}

QLabel[tone="neutral"] {
    background: #263348;
    color: #d1d5db;
}

QLabel[tone="warning"] {
    background: #4a3414;
    color: #fde68a;
}

QLabel[tone="danger"] {
    background: #4c1717;
    color: #fecaca;
}

QLabel[tone="working"] {
    background: #35275c;
    color: #ddd6fe;
}

QGroupBox {
    background: #172033;
    border: 1px solid #2f3b52;
    border-radius: 8px;
    font-weight: 700;
    margin-top: 14px;
    padding: 14px;
}

QGroupBox::title {
    color: #f9fafb;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QLineEdit,
QSpinBox,
QTextEdit {
    background: #0f172a;
    border: 1px solid #374151;
    border-radius: 6px;
    color: #f9fafb;
    padding: 7px 9px;
}

QLineEdit:focus,
QSpinBox:focus,
QTextEdit:focus {
    border-color: #60a5fa;
}

QPushButton {
    background: #263348;
    border: 1px solid #3f4b63;
    border-radius: 6px;
    color: #f9fafb;
    font-weight: 700;
    padding: 8px 14px;
}

QPushButton:hover {
    background: #334155;
}

QPushButton#primaryButton {
    background: #1d4ed8;
    border-color: #2563eb;
}

QPushButton#primaryButton:hover {
    background: #2563eb;
}

QPushButton#warningButton {
    background: #92400e;
    border-color: #b45309;
}

QPushButton#dangerButton {
    background: #991b1b;
    border-color: #b91c1c;
}

QLabel#inferenceImage {
    background: #050816;
    border: 1px solid #2f3b52;
    border-radius: 8px;
    color: #9ca3af;
}

QTextEdit#activityLog {
    font-family: Consolas, "Cascadia Mono", monospace;
}

QProgressBar {
    background: #0f172a;
    border: 1px solid #374151;
    border-radius: 4px;
    height: 8px;
}

QProgressBar::chunk {
    background: #38bdf8;
    border-radius: 4px;
}
"""
