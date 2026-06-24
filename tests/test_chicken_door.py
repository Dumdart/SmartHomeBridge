import asyncio
from types import SimpleNamespace

from smart_home_bridge.bridge_devices.chicken_door import (
    chicken_door,
    chicken_door_mqtt_callbacks,
    door_controller,
    door_position,
)
from smart_home_bridge.bridge_devices.chicken_door.chicken_door_message import (
    handle_chicken_door_mqtt_message,
)
from smart_home_bridge.config import HttpConfig, MqttConfig, app_config, DoorApiConfig
from smart_home_bridge.infrastructure.api.http_gate import HttpGateInterface


class FakeHttpGate(HttpGateInterface):
    def get(self, endpoint, params=None):
        return None

    def post(self, endpoint, data=None):
        return None

    def put(self, endpoint, data=None):
        return None

    def delete(self, endpoint):
        return None


def test_controller_executes_close_command():
    door = chicken_door(1, "door", door_position.OPEN)
    controller = door_controller(door, FakeHttpGate())

    asyncio.run(controller.excecute_command("close_door"))

    assert door.position == door_position.CLOSED


def test_command_publishes_resulting_state_with_publishable_field():
    published_payloads = []
    door = chicken_door(1, "door", door_position.CLOSED)

    async def publishable(payload):
        published_payloads.append(payload)

    controller = door_controller(door, FakeHttpGate(), publishable)

    result = asyncio.run(controller.excecute_command("open_door"))

    assert result.success is True
    assert result.data == door_position.OPEN
    assert published_payloads == ["open"]


def test_mqtt_callback_decodes_payload_and_executes_command():
    door = chicken_door(1, "door", door_position.CLOSED)
    controller = door_controller(door, FakeHttpGate())
    callbacks = chicken_door_mqtt_callbacks(controller)
    message = SimpleNamespace(topic="loxone/chicken-door", payload=b"open_door")

    callbacks.on_message(None, None, message)

    assert door.position == door_position.OPEN


def test_door_message_decodes_payload_and_executes_command():
    door = chicken_door(1, "door", door_position.CLOSED)
    controller = door_controller(door, FakeHttpGate())

    asyncio.run(
        handle_chicken_door_mqtt_message(
            "loxone/chicken-door",
            b" open_door ",
            controller,
        )
    )

    assert door.position == door_position.OPEN


def test_application_entrypoint_imports():
    from smart_home_bridge.__main__ import App

    assert App.__name__ == "App"


def test_application_wires_door_commands_to_mqtt_publish():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
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
    )
    app = App(config)
    app.door.position = door_position.CLOSED
    published = []

    class FakeMqttClient:
        async def publish(self, topic, payload, on_publish=None):
            published.append((topic, payload))

    app.chicken_door_mqtt_gate.client = FakeMqttClient()

    result = asyncio.run(app.door_controller.excecute_command("open_door"))

    assert result.success is True
    assert result.data == door_position.OPEN
    assert published == [("loxone/chicken-door", "open")]
