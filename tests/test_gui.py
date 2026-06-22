import asyncio
from pathlib import Path

from loxone_bridge.bridge_devices.chicken_door import door_position
from loxone_bridge.config import DoorApiConfig, HttpConfig, MqttConfig, app_config
from loxone_bridge.gui import run
from loxone_bridge.gui.factory import create_gui_bridge_context


def _config():
    return app_config(
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


def test_gui_entrypoint_imports_without_pyside6():
    assert callable(run)


def test_gui_context_wires_chicken_door_controller():
    context = create_gui_bridge_context(_config())

    assert context.door.position == door_position.UNKNOWN
    assert context.door_controller.device is context.door
    assert context.command_topic == "loxone/chicken-door"
    assert context.activity_log.log_file_path == Path("logs/loxone-bridge.log")


def test_gui_context_controller_executes_commands():
    context = create_gui_bridge_context(_config())
    context.door.position = door_position.CLOSED

    result = asyncio.run(context.door_controller.excecute_command("open_door"))

    assert result.success is True
    assert context.door.position == door_position.OPEN
