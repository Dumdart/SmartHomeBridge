from dataclasses import replace
from typing import Protocol

from smart_home_bridge.bridge_devices.chicken_door import chicken_door
from smart_home_bridge.bridge_devices.chicken_thread_detector import chicken_thread_detector
from smart_home_bridge.config import app_config
from smart_home_contracts.chicken_thread import DangerAssessment
from smart_home_bridge.gui.view_model import GuiBridgeSnapshot, snapshot_from_config


class GuiBackendObserver(Protocol):
    def snapshot(self) -> GuiBridgeSnapshot: ...


class LocalCompositionObserver:
    def __init__(
        self,
        config: app_config,
        door: chicken_door,
        threat_detector: chicken_thread_detector,
        command_topic: str,
        detector_topic: str,
    ):
        self.config = config
        self.door = door
        self.threat_detector = threat_detector
        self.command_topic = command_topic
        self.detector_topic = detector_topic
        self.camera_health = "Unknown"
        self.backend_status = "Ready"
        self.last_activity_entries: tuple[str, ...] = ()

    def snapshot(self) -> GuiBridgeSnapshot:
        return snapshot_from_config(
            config=self.config,
            door_state=self.door.position.value,
            threat_assessment=self.threat_detector.assessment,
            command_topic=self.command_topic,
            detector_topic=self.detector_topic,
            camera_health=self.camera_health,
            backend_status=self.backend_status,
            last_activity_entries=self.last_activity_entries,
        )

    def update_config(self, config: app_config):
        self.config = config

    def update_camera_health(self, value: str):
        self.camera_health = value

    def update_backend_status(self, value: str):
        self.backend_status = value

    def update_activity_entries(self, entries: tuple[str, ...]):
        self.last_activity_entries = entries


class MqttStatusObserver:
    def __init__(self, snapshot: GuiBridgeSnapshot):
        self._snapshot = snapshot

    def snapshot(self) -> GuiBridgeSnapshot:
        return self._snapshot

    def update_door_state(self, state: str):
        self._snapshot = replace(self._snapshot, door_state=state)

    def update_threat_assessment(self, assessment: DangerAssessment):
        self._snapshot = replace(self._snapshot, threat_assessment=assessment)

    def update_camera_health(self, value: str):
        self._snapshot = replace(self._snapshot, camera_health=value)

    def update_backend_status(self, value: str):
        self._snapshot = replace(self._snapshot, backend_status=value)
