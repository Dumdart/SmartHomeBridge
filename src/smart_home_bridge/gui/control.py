from collections.abc import Callable
from typing import Protocol

from smart_home_bridge.bridge_devices.chicken_door import door_controller
from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.config import MqttConfig
from smart_home_bridge.core.command import command_result
from smart_home_bridge.gui.threat_detection import GuiThreatScanResult, GuiThreatScanService
from smart_home_bridge.infrastructure.mqtt.mqtt_client import MqttClient
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttAdapter


class GuiBackendControl(Protocol):
    async def execute_door_command(self, command_name: str) -> command_result: ...


class GuiThreatDiagnosticControl(Protocol):
    def camera_health(self) -> bool: ...

    async def run_scan_once(self) -> GuiThreatScanResult: ...


class LocalBackendControl:
    def __init__(self, door_controller: door_controller):
        self.door_controller = door_controller

    async def execute_door_command(self, command_name: str) -> command_result:
        return await self.door_controller.excecute_command(command_name)


class MqttBackendControl:
    def __init__(
        self,
        mqtt_config: MqttConfig,
        command_topic: str,
        mqtt_client_factory: Callable[[MqttConfig], MqttAdapter] = MqttClient,
    ):
        self.mqtt_config = mqtt_config
        self.command_topic = command_topic
        self.mqtt_client_factory = mqtt_client_factory

    async def execute_door_command(self, command_name: str) -> command_result:
        client: MqttAdapter = self.mqtt_client_factory(self.mqtt_config)
        await client.connect()
        try:
            await client.publish(self.command_topic, command_name)
        finally:
            await client.disconnect()

        return command_result()


class LocalThreatDiagnosticControl:
    def __init__(self, threat_scan_service: GuiThreatScanService):
        self.threat_scan_service = threat_scan_service

    @property
    def detector_controller(self) -> chicken_thread_detector_controller:
        return self.threat_scan_service.detector_controller

    def camera_health(self) -> bool:
        return self.threat_scan_service.camera_client.health()

    async def run_scan_once(self) -> GuiThreatScanResult:
        return await self.threat_scan_service.scan_once()
