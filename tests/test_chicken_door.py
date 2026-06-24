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
from smart_home_bridge.bridge_devices.chicken_door.door_controller import (
    CLOSE_DOOR_COMMAND,
    GET_DOOR_STATE_COMMAND,
    OPEN_DOOR_COMMAND,
    STOP_DOOR_COMMAND,
    close_door_command,
    get_door_state_command,
    open_door_command,
    stop_door_command,
)
from smart_home_bridge.config import HttpConfig, MqttConfig, app_config, DoorApiConfig


def test_open_command_updates_and_publishes_door_state():
    published_payloads = []
    door = chicken_door(1, "door", door_position.CLOSED)

    async def publishable(payload):
        published_payloads.append(payload)

    result = asyncio.run(open_door_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.OPEN
    assert door.position == door_position.OPEN
    assert published_payloads == ["open"]


def test_close_command_updates_and_publishes_door_state():
    published_payloads = []
    door = chicken_door(1, "door", door_position.OPEN)

    async def publishable(payload):
        published_payloads.append(payload)

    result = asyncio.run(close_door_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.CLOSED
    assert door.position == door_position.CLOSED
    assert published_payloads == ["closed"]


def test_stop_command_preserves_and_publishes_current_state():
    published_payloads = []
    door = chicken_door(1, "door", door_position.UNKNOWN)

    async def publishable(payload):
        published_payloads.append(payload)

    result = asyncio.run(stop_door_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.UNKNOWN
    assert door.position == door_position.UNKNOWN
    assert published_payloads == ["unknown"]


def test_get_state_command_publishes_current_state():
    published_payloads = []
    door = chicken_door(1, "door", door_position.OPEN)

    async def publishable(payload):
        published_payloads.append(payload)

    result = asyncio.run(get_door_state_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.OPEN
    assert published_payloads == ["open"]


def test_controller_resolves_supported_door_commands():
    door = chicken_door(1, "door", door_position.UNKNOWN)
    controller = door_controller(door)

    assert isinstance(controller.get_command(OPEN_DOOR_COMMAND), open_door_command)
    assert isinstance(controller.get_command(CLOSE_DOOR_COMMAND), close_door_command)
    assert isinstance(controller.get_command(STOP_DOOR_COMMAND), stop_door_command)
    assert isinstance(controller.get_command(GET_DOOR_STATE_COMMAND), get_door_state_command)


def test_controller_executes_close_command():
    door = chicken_door(1, "door", door_position.OPEN)
    controller = door_controller(door)

    asyncio.run(controller.excecute_command(CLOSE_DOOR_COMMAND))

    assert door.position == door_position.CLOSED


def test_mqtt_callback_decodes_payload_and_executes_command():
    door = chicken_door(1, "door", door_position.CLOSED)
    controller = door_controller(door)
    callbacks = chicken_door_mqtt_callbacks(controller)
    message = SimpleNamespace(topic="loxone/chicken-door", payload=b"open_door")

    callbacks.on_message(None, None, message)

    assert door.position == door_position.OPEN


def test_door_message_decodes_payload_and_executes_command():
    door = chicken_door(1, "door", door_position.CLOSED)
    controller = door_controller(door)

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

    result = asyncio.run(app.door_controller.excecute_command(OPEN_DOOR_COMMAND))

    assert result.success is True
    assert result.data == door_position.OPEN
    assert published == [("loxone/chicken-door", "open")]
