import asyncio

import pytest

from smart_home_bridge import __main__ as main
from smart_home_bridge.config import (
    BridgeDeviceConfig,
    BridgeDevicesConfig,
    DoorApiConfig,
    HttpConfig,
    MqttConfig,
    app_config,
)


def test_publish_door_command_sends_allowed_command_to_configured_topic(monkeypatch):
    events = []

    class FakeMqttClient:
        def __init__(self, mqtt_config):
            events.append(("init", mqtt_config.host))

        async def connect(self):
            events.append(("connect",))

        async def publish(self, topic, payload):
            events.append(("publish", topic, payload))

        async def disconnect(self):
            events.append(("disconnect",))

    monkeypatch.setattr(main, "MqttClient", FakeMqttClient)
    monkeypatch.setattr(main, "load_app_config", _config)

    asyncio.run(main._publish_door_command("open_door"))

    assert events == [
        ("init", "mqtt.local"),
        ("connect",),
        ("publish", "smart-home-bridge/coop/door/command", "open_door"),
        ("disconnect",),
    ]


def test_publish_door_command_rejects_unknown_command(monkeypatch):
    monkeypatch.setattr(main, "load_app_config", _config)

    with pytest.raises(ValueError):
        asyncio.run(main._publish_door_command("format_disk"))


def _config():
    return app_config(
        door_api=DoorApiConfig(api_key="api-key", device_id="device-id"),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=1883,
            username="user",
            password="password",
            base_topic="smart-home-bridge",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        devices=BridgeDevicesConfig(
            enabled=("chicken_door",),
            configs={
                "chicken_door": BridgeDeviceConfig(
                    key="chicken_door",
                    topics={"command": "coop/door/command"},
                ),
            },
        ),
    )
