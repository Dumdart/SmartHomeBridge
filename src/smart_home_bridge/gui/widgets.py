from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from smart_home_bridge.config import HttpConfig, MqttConfig, app_config


def set_badge_tone(widget: QLabel, tone: str):
    widget.setProperty("tone", tone)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _badge(text: str, object_name: str, tone: str = "neutral") -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setProperty("tone", tone)
    return label


def _panel_layout(widget: QFrame, title: str, object_name: str) -> QVBoxLayout:
    widget.setObjectName(object_name)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(12)

    title_label = QLabel(title)
    title_label.setObjectName("panelTitle")
    layout.addWidget(title_label)
    return layout


def _detail_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("detailLabel")
    return label


def _detail_value(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("detailValue")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class StatusStrip(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("statusStrip")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        title_block = QVBoxLayout()
        title_block.setSpacing(3)

        title = QLabel("Smart Home Bridge")
        title.setObjectName("appTitle")
        subtitle = QLabel(
            "Local bridge control for chicken door, MQTT, diagnostics, and threat scans."
        )
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block, 1)

        self.door_value = _badge("unknown", "doorStateValue")
        self.threat_value = _badge("none", "threatLevelValue", "good")
        self.bridge_value = _badge("Ready", "statusValue", "good")
        self.camera_value = _badge("Unknown", "statusStripCameraValue")

        layout.addWidget(self._status_card("Door", self.door_value))
        layout.addWidget(self._status_card("Threat", self.threat_value))
        layout.addWidget(self._status_card("Bridge", self.bridge_value))
        layout.addWidget(self._status_card("Camera", self.camera_value))

    def _status_card(self, label: str, value: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("statusCard")
        card.setMinimumWidth(116)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(6)

        label_widget = QLabel(label)
        label_widget.setObjectName("statusLabel")
        layout.addWidget(label_widget)
        layout.addWidget(value)
        return card

    def set_door(self, value: str, tone: str):
        self.door_value.setText(value)
        set_badge_tone(self.door_value, tone)

    def set_threat(self, value: str, tone: str):
        self.threat_value.setText(value)
        set_badge_tone(self.threat_value, tone)

    def set_bridge(self, value: str, tone: str):
        self.bridge_value.setText(value)
        set_badge_tone(self.bridge_value, tone)

    def set_camera(self, value: str, tone: str):
        self.camera_value.setText(value)
        set_badge_tone(self.camera_value, tone)


class DoorControlPanel(QFrame):
    command_requested = Signal(str)

    def __init__(self):
        super().__init__()
        layout = _panel_layout(self, "Chicken Door", "operatorPanel")

        self.state_value = _badge("unknown", "doorPanelStateValue")
        layout.addWidget(self._state_surface())
        layout.addWidget(self._command_surface())
        layout.addStretch(1)

    def _state_surface(self) -> QFrame:
        surface = QFrame()
        surface.setObjectName("controlSurface")
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label = QLabel("Current position")
        label.setObjectName("statusLabel")
        layout.addWidget(label)
        layout.addWidget(self.state_value)
        return surface

    def _command_surface(self) -> QFrame:
        surface = QFrame()
        surface.setObjectName("controlSurface")
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        for label, command_name, object_name in (
            ("Open Door", "open_door", "primaryButton"),
            ("Close Door", "close_door", "warningButton"),
            ("Stop", "stop_door", "dangerButton"),
            ("Refresh State", "get_door_state", ""),
        ):
            button = QPushButton(label)
            if object_name:
                button.setObjectName(object_name)
            button.clicked.connect(
                lambda _checked=False, name=command_name: self.command_requested.emit(name)
            )
            layout.addWidget(button)

        return surface

    def set_state(self, value: str, tone: str):
        self.state_value.setText(value)
        set_badge_tone(self.state_value, tone)


class ThreatDetectorPanel(QFrame):
    scan_requested = Signal()
    health_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = _panel_layout(self, "Chicken Threat Detector", "threatPanel")

        self.level_value = _badge("none", "threatLevelValue", "good")
        self.score_value = _detail_value("0.0000")
        self.count_value = _detail_value("0")
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 10000)
        self.score_bar.setTextVisible(False)

        self.image_label = QLabel("No inferred frame")
        self.image_label.setObjectName("inferenceImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(520, 340)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.image_label.setScaledContents(False)
        self._inference_pixmap = QPixmap()

        layout.addWidget(self._toolbar())
        layout.addWidget(self._metrics_surface())

        caption = QLabel("Latest annotated camera frame")
        caption.setObjectName("sectionCaption")
        layout.addWidget(caption)
        layout.addWidget(self.image_label, 1)

    def _toolbar(self) -> QWidget:
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        scan_button = QPushButton("Run Inference")
        scan_button.setObjectName("primaryButton")
        scan_button.clicked.connect(self.scan_requested.emit)

        health_button = QPushButton("Check Health")
        health_button.clicked.connect(self.health_requested.emit)

        layout.addWidget(scan_button)
        layout.addWidget(health_button)
        layout.addStretch(1)
        return toolbar

    def _metrics_surface(self) -> QFrame:
        surface = QFrame()
        surface.setObjectName("detailSurface")
        layout = QGridLayout(surface)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(1, 1)

        layout.addWidget(_detail_label("Threat level"), 0, 0)
        layout.addWidget(self.level_value, 0, 1)
        layout.addWidget(_detail_label("Detector score"), 1, 0)
        layout.addWidget(self.score_value, 1, 1)
        layout.addWidget(self.score_bar, 2, 1)
        layout.addWidget(_detail_label("Detections"), 3, 0)
        layout.addWidget(self.count_value, 3, 1)
        return surface

    def set_assessment(self, level: str, score: float, count: int, tone: str):
        self.level_value.setText(level)
        set_badge_tone(self.level_value, tone)
        self.score_value.setText(f"{score:.4f}")
        self.score_bar.setValue(max(0, min(10000, int(score * 10000))))
        self.count_value.setText(str(count))

    def render_image(self, image_bytes: bytes) -> bool:
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_bytes):
            self._inference_pixmap = QPixmap()
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Could not render inferred frame")
            return False

        self._inference_pixmap = pixmap
        self.update_inference_pixmap()
        return True

    def update_inference_pixmap(self):
        if self._inference_pixmap.isNull():
            return

        scaled = self._inference_pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_inference_pixmap()


class DiagnosticsPanel(QFrame):
    def __init__(self):
        super().__init__()
        layout = _panel_layout(self, "Diagnostics", "diagnosticsPanel")

        self.mqtt_topic_value = _detail_value()
        self.detector_topic_value = _detail_value()
        self.http_endpoint_value = _detail_value()
        self.camera_endpoint_value = _detail_value()
        self.camera_health_value = _badge("Unknown", "cameraHealthValue")

        surface = QFrame()
        surface.setObjectName("detailSurface")
        grid = QGridLayout(surface)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(9)
        grid.setColumnStretch(1, 1)

        self._add_detail(grid, 0, "MQTT topic", self.mqtt_topic_value)
        self._add_detail(grid, 1, "Detector topic", self.detector_topic_value)
        self._add_detail(grid, 2, "HTTP diagnostics", self.http_endpoint_value)
        self._add_detail(grid, 3, "Camera endpoint", self.camera_endpoint_value)
        self._add_detail(grid, 4, "Camera health", self.camera_health_value)

        layout.addWidget(surface)
        layout.addStretch(1)

    def _add_detail(self, layout: QGridLayout, row: int, label: str, value: QLabel):
        layout.addWidget(_detail_label(label), row, 0)
        layout.addWidget(value, row, 1)

    def set_details(
        self,
        mqtt_topic: str,
        detector_topic: str,
        http_endpoint: str,
        camera_endpoint: str,
    ):
        self.mqtt_topic_value.setText(mqtt_topic)
        self.detector_topic_value.setText(detector_topic)
        self.http_endpoint_value.setText(http_endpoint)
        self.camera_endpoint_value.setText(camera_endpoint)

    def set_camera_health(self, value: str, tone: str):
        self.camera_health_value.setText(value)
        set_badge_tone(self.camera_health_value, tone)


class EnvironmentPanel(QFrame):
    save_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = _panel_layout(self, "Environment", "environmentPanel")

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

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(9)
        form.addRow("MQTT host", self.mqtt_host_input)
        form.addRow("MQTT port", self.mqtt_port_input)
        form.addRow("MQTT username", self.mqtt_username_input)
        form.addRow("MQTT password", self.mqtt_password_input)
        form.addRow("MQTT base topic", self.mqtt_base_topic_input)
        form.addRow("HTTP host", self.http_host_input)
        form.addRow("HTTP port", self.http_port_input)

        save_button = QPushButton("Save Environment")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_requested.emit)
        form.addRow(save_button)

        layout.addLayout(form)

    def set_config(self, config: app_config):
        self.mqtt_host_input.setText(config.mqtt.host)
        self.mqtt_port_input.setValue(config.mqtt.port)
        self.mqtt_username_input.setText(config.mqtt.username)
        self.mqtt_password_input.setText(config.mqtt.password)
        self.mqtt_base_topic_input.setText(config.mqtt.base_topic)
        self.http_host_input.setText(config.http.host)
        self.http_port_input.setValue(config.http.port)

    def mqtt_config(self) -> MqttConfig:
        return MqttConfig(
            host=self.mqtt_host_input.text().strip(),
            port=self.mqtt_port_input.value(),
            username=self.mqtt_username_input.text().strip(),
            password=self.mqtt_password_input.text(),
            base_topic=self.mqtt_base_topic_input.text().strip(),
        )

    def http_config(self) -> HttpConfig:
        return HttpConfig(
            host=self.http_host_input.text().strip(),
            port=self.http_port_input.value(),
        )


class ActivityLogPanel(QFrame):
    def __init__(self):
        super().__init__()
        layout = _panel_layout(self, "Activity", "activityPanel")

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        self.log_output.setObjectName("activityLog")
        layout.addWidget(self.log_output)

    def append_entry(self, entry: str):
        self.log_output.append(entry)
