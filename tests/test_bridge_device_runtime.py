import asyncio

from smart_home_bridge.bridge_devices.runtime import (
    BridgeDeviceMqttBinding,
    BridgeDeviceRuntime,
)
from smart_home_bridge.config import MqttConfig


def test_bridge_device_runtime_starts_and_stops_mqtt_and_lifecycle_services():
    events = []
    gate = FakeGate(events)
    service = FakeBackgroundService(events)
    runtime = BridgeDeviceRuntime(
        name="test_device",
        mqtt_config=_mqtt_config(),
        mqtt_bindings=(
            BridgeDeviceMqttBinding(
                name="commands",
                topic="test-device/command",
                gate=gate,
                publish_topics=("loxone/test-device/status",),
            ),
        ),
        background_services=(service,),
    )

    asyncio.run(runtime.start())
    asyncio.run(runtime.stop())

    assert events == [
        "gate.start",
        "gate.subscribe",
        "service.start",
        "service.stop",
        "gate.stop",
    ]
    assert runtime.mqtt_gates == (gate,)
    assert runtime.is_running is False
    assert runtime.mqtt_running is False
    assert runtime.background_services_running is False


def test_bridge_device_runtime_tracks_running_state_after_start():
    events = []
    gate = FakeGate(events)
    service = FakeBackgroundService(events)
    runtime = BridgeDeviceRuntime(
        name="test_device",
        mqtt_config=_mqtt_config(),
        mqtt_bindings=(
            BridgeDeviceMqttBinding(
                name="commands",
                topic="test-device/command",
                gate=gate,
            ),
        ),
        background_services=(service,),
    )

    asyncio.run(runtime.start())

    assert runtime.is_running is True
    assert runtime.mqtt_running is True
    assert runtime.background_services_running is True

    asyncio.run(runtime.stop())


class FakeGate:
    def __init__(self, events):
        self.events = events

    async def start(self):
        self.events.append("gate.start")

    async def subscribe(self):
        self.events.append("gate.subscribe")

    async def stop(self):
        self.events.append("gate.stop")


class FakeBackgroundService:
    def __init__(self, events):
        self.events = events

    async def start(self):
        self.events.append("service.start")

    async def stop(self):
        self.events.append("service.stop")


def _mqtt_config() -> MqttConfig:
    return MqttConfig(
        host="mqtt.local",
        port=8883,
        username="user",
        password="password",
        base_topic="loxone",
    )
