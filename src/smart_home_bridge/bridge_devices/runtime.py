from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from smart_home_bridge.config import BridgeDeviceConfig, MqttConfig
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttAdapter, MqttGate

MqttClientFactory = Callable[[MqttConfig], MqttAdapter]


class BackgroundService(Protocol):
    async def start(self): ...

    async def stop(self): ...


def build_topic(base_topic: str, topic: str) -> str:
    return f"{base_topic.rstrip('/')}/{topic.strip('/')}"


@dataclass(frozen=True)
class BridgeDeviceMqttBinding:
    name: str
    topic: str
    gate: MqttGate
    ignore_retained: bool = True
    publish_topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class BridgeDeviceComposition:
    key: str
    config: BridgeDeviceConfig
    handles: dict[str, Any]
    create_runtime: Callable[[MqttClientFactory], BridgeDeviceRuntime]

    @property
    def name(self) -> str:
        return self.config.name or self.key


@dataclass
class BridgeDeviceRuntime:
    name: str
    mqtt_config: MqttConfig
    mqtt_bindings: tuple[BridgeDeviceMqttBinding, ...] = ()
    background_services: tuple[BackgroundService, ...] = ()
    handles: dict[str, Any] = field(default_factory=dict)

    @property
    def mqtt_gates(self) -> tuple[MqttGate, ...]:
        return tuple(binding.gate for binding in self.mqtt_bindings)

    async def start(self):
        for binding in self.mqtt_bindings:
            await binding.gate.start()
            await binding.gate.subscribe()

        for service in self.background_services:
            await service.start()

    async def stop(self):
        for service in reversed(self.background_services):
            await service.stop()

        for binding in reversed(self.mqtt_bindings):
            await binding.gate.stop()
