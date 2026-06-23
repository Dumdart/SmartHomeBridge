import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
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
        self.resize(520, 420)

        self.state_value = QLabel(self.context.door.position.value)
        self.state_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_value.setObjectName("doorStateValue")

        self.mqtt_topic_value = QLabel(self.context.command_topic)
        self.http_endpoint_value = QLabel(self._http_endpoint())
        self.status_value = QLabel("Ready")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

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
        self._append_log("GUI started.")

    def _build_layout(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        layout.addWidget(self._build_status_group())
        layout.addWidget(self._build_settings_group())
        layout.addWidget(self._build_command_group())
        layout.addWidget(self._build_log_group())

        self.setCentralWidget(root)

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("Bridge Status")
        layout = QGridLayout(group)

        layout.addWidget(QLabel("Door state"), 0, 0)
        layout.addWidget(self.state_value, 0, 1)
        layout.addWidget(QLabel("MQTT topic"), 1, 0)
        layout.addWidget(self.mqtt_topic_value, 1, 1)
        layout.addWidget(QLabel("HTTP diagnostics"), 2, 0)
        layout.addWidget(self.http_endpoint_value, 2, 1)
        layout.addWidget(QLabel("Status"), 3, 0)
        layout.addWidget(self.status_value, 3, 1)

        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("Environment Settings")
        layout = QFormLayout(group)

        layout.addRow("MQTT host", self.mqtt_host_input)
        layout.addRow("MQTT port", self.mqtt_port_input)
        layout.addRow("MQTT username", self.mqtt_username_input)
        layout.addRow("MQTT password", self.mqtt_password_input)
        layout.addRow("MQTT base topic", self.mqtt_base_topic_input)
        layout.addRow("HTTP host", self.http_host_input)
        layout.addRow("HTTP port", self.http_port_input)

        save_button = QPushButton("Save Environment")
        save_button.clicked.connect(self._save_environment_settings)
        layout.addRow(save_button)

        return group

    def _build_command_group(self) -> QGroupBox:
        group = QGroupBox("Chicken Door")
        layout = QHBoxLayout(group)

        commands = [
            ("Open", "open_door"),
            ("Close", "close_door"),
            ("Stop", "stop_door"),
            ("Refresh", "get_door_state"),
        ]

        for label, command_name in commands:
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, name=command_name: self._run_command(name)
            )
            layout.addWidget(button)

        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Activity")
        layout = QVBoxLayout(group)
        layout.addWidget(self.log_output)
        return group

    def _run_command(self, command_name: str):
        self.status_value.setText(f"Running {command_name}")

        try:
            result = asyncio.run(
                self.context.door_controller.excecute_command(command_name)
            )
        except Exception as exc:
            self.status_value.setText("Command failed")
            self._append_log(f"{command_name} failed: {exc}")
            return

        state = result.data
        if isinstance(state, door_position):
            self.state_value.setText(state.value)

        self.status_value.setText("Ready")
        self._append_log(
            f"{command_name} completed with state {self.context.door.position.value}."
        )

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
        self.status_value.setText("Saving environment")

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
            self.status_value.setText("Save failed")
            self._append_log(f"Environment save failed: {exc}")
            return

        previous_state = self.context.door.position
        self.context = create_gui_bridge_context(config, self.context.env_settings)
        self.context.door.position = previous_state
        self._refresh_status_labels()

        self.status_value.setText("Ready")
        self._append_log("Environment settings saved.")

    def _refresh_status_labels(self):
        self.state_value.setText(self.context.door.position.value)
        self.mqtt_topic_value.setText(self.context.command_topic)
        self.http_endpoint_value.setText(self._http_endpoint())

    def _http_endpoint(self) -> str:
        return f"{self.context.config.http.host}:{self.context.config.http.port}"
