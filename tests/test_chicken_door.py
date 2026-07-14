import asyncio
import json
from types import SimpleNamespace

from smart_home_bridge.bridge_devices.chicken_door import (
    chicken_door,
    chicken_door_mqtt_callbacks,
    door_controller,
    door_position,
    door_status,
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
    published_statuses = []
    door = chicken_door(1, "door", door_position.CLOSED)

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(open_door_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.OPEN
    assert door.position == door_position.OPEN
    assert published_statuses == [door_status(door_position.OPEN)]


def test_close_command_updates_and_publishes_door_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.OPEN)

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(close_door_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.CLOSED
    assert door.position == door_position.CLOSED
    assert published_statuses == [door_status(door_position.CLOSED)]


def test_stop_command_preserves_and_publishes_current_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.UNKNOWN)

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(stop_door_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.UNKNOWN
    assert door.position == door_position.UNKNOWN
    assert published_statuses == [door_status(door_position.UNKNOWN)]


def test_get_state_command_publishes_current_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.OPEN)

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(get_door_state_command(door, publishable).excecute())

    assert result.success is True
    assert result.data == door_position.OPEN
    assert published_statuses == [door_status(door_position.OPEN)]


def test_open_command_uses_gateway_and_publishes_returned_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.CLOSED)
    gateway = FakeDoorGateway(open_status=door_status(door_position.OPEN_PENDING))

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(open_door_command(door, publishable, gateway).excecute())

    assert result.success is True
    assert result.data == door_position.OPEN_PENDING
    assert door.position == door_position.OPEN_PENDING
    assert gateway.calls == ["open"]
    assert published_statuses == [door_status(door_position.OPEN_PENDING)]


def test_close_command_uses_gateway_and_publishes_returned_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.OPEN)
    gateway = FakeDoorGateway(close_status=door_status(door_position.CLOSE_PENDING))

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(close_door_command(door, publishable, gateway).excecute())

    assert result.success is True
    assert result.data == door_position.CLOSE_PENDING
    assert door.position == door_position.CLOSE_PENDING
    assert gateway.calls == ["close"]
    assert published_statuses == [door_status(door_position.CLOSE_PENDING)]


def test_stop_command_uses_gateway_and_publishes_returned_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.OPENING)
    gateway = FakeDoorGateway(stop_status=door_status(door_position.STOPPING))

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(stop_door_command(door, publishable, gateway).excecute())

    assert result.success is True
    assert result.data == door_position.STOPPING
    assert door.position == door_position.STOPPING
    assert gateway.calls == ["stop"]
    assert published_statuses == [door_status(door_position.STOPPING)]


def test_get_state_command_uses_gateway_and_publishes_returned_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.UNKNOWN)
    gateway = FakeDoorGateway(state_status=door_status(door_position.CLOSED))

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(get_door_state_command(door, publishable, gateway).excecute())

    assert result.success is True
    assert result.data == door_position.CLOSED
    assert door.position == door_position.CLOSED
    assert gateway.calls == ["get_state"]
    assert published_statuses == [door_status(door_position.CLOSED)]


def test_gateway_error_returns_failed_result_without_overwriting_state():
    published_statuses = []
    door = chicken_door(1, "door", door_position.OPEN)
    gateway = FakeDoorGateway(error=ValueError("missing action"))

    async def publishable(status):
        published_statuses.append(status)

    result = asyncio.run(close_door_command(door, publishable, gateway).excecute())

    assert result.success is False
    assert result.data == door_position.OPEN
    assert door.position == door_position.OPEN
    assert gateway.calls == ["close"]
    assert published_statuses == []


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
    message = SimpleNamespace(
        topic="loxone/chicken-door/command",
        payload=b"open_door",
        retain=False,
    )

    callbacks.on_message(None, None, message)

    assert door.position == door_position.OPEN


def test_mqtt_callback_ignores_retained_command_message():
    door = chicken_door(1, "door", door_position.CLOSED)
    controller = door_controller(door)
    callbacks = chicken_door_mqtt_callbacks(controller)
    message = SimpleNamespace(
        topic="loxone/chicken-door/command",
        payload=b"open_door",
        retain=True,
    )

    callbacks.on_message(None, None, message)

    assert door.position == door_position.CLOSED


def test_door_message_decodes_payload_and_executes_command():
    door = chicken_door(1, "door", door_position.CLOSED)
    controller = door_controller(door)

    asyncio.run(
        handle_chicken_door_mqtt_message(
            "loxone/chicken-door/command",
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
    from smart_home_bridge.bridge_devices.registry import create_bridge_device_compositions
    from smart_home_bridge.composition import create_bridge_composition

    config = app_config(
        door_api=DoorApiConfig(
            api_key="api-key",
            device_id="device-id",
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
    published = []

    class FakeMqttClient:
        async def publish(self, topic, payload, retain=False, on_publish=None):
            published.append((topic, payload, retain))

    app = App(
        config,
        mqtt_client_factory=lambda _: FakeMqttClient(),
        composition_factory=lambda config: create_bridge_composition(
            config,
            device_composition_factory=lambda config: create_bridge_device_compositions(
                config,
                door_gateway_factory=lambda _: None,
            ),
        ),
    )
    app.door.position = door_position.CLOSED

    result = asyncio.run(app.door_controller.excecute_command(OPEN_DOOR_COMMAND))

    assert result.success is True
    assert result.data == door_position.OPEN
    assert published[:6] == [
        ("loxone/chicken-door/status", "open", True),
        ("loxone/chicken-door/status_code", "1", True),
        ("loxone/chicken-door/fault", "none", True),
        ("loxone/chicken-door/connected", "1", True),
        ("loxone/chicken-door/battery", "100", True),
        ("loxone/chicken-door/light_level", "0", True),
    ]
    usage_topic, usage_payload, usage_retain = published[6]
    usage = json.loads(usage_payload)
    assert usage_topic == "loxone/chicken-door"
    assert usage_retain is False
    assert usage["event"] == "chicken_door_command"
    assert usage["command"] == "open_door"
    assert usage["success"] is True
    assert usage["position"] == "open"
    assert "timestamp" in usage


class FakeDoorGateway:
    def __init__(
        self,
        state_status: door_status | None = None,
        open_status: door_status | None = None,
        close_status: door_status | None = None,
        stop_status: door_status | None = None,
        error: Exception | None = None,
    ):
        self.state_status = state_status or door_status(door_position.UNKNOWN)
        self.open_status = open_status or door_status(door_position.OPEN)
        self.close_status = close_status or door_status(door_position.CLOSED)
        self.stop_status = stop_status or door_status(door_position.UNKNOWN)
        self.error = error
        self.calls = []

    def get_state(self):
        self.calls.append("get_state")
        return self._result(self.state_status)

    def open(self):
        self.calls.append("open")
        return self._result(self.open_status)

    def close(self):
        self.calls.append("close")
        return self._result(self.close_status)

    def stop(self):
        self.calls.append("stop")
        return self._result(self.stop_status)

    def _result(self, status):
        if self.error is not None:
            raise self.error
        return status
