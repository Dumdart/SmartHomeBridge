import asyncio

from smart_home_bridge.bridge_devices.chicken_door import door_position, door_status
from smart_home_bridge.bridge_devices.chicken_door.door_mqtt_publisher import (
    DoorMqttPublisher,
    DoorMqttTopics,
    to_status_code,
)


def test_open_status_publishes_scalar_topics_with_status_code():
    published = []
    publisher = DoorMqttPublisher(_topics(), _collect(published))

    asyncio.run(publisher.publish_status(door_status(door_position.OPEN)))

    assert published[0] == ("base/chicken-door/status", "open", True)
    assert published[1] == ("base/chicken-door/status_code", "1", True)


def test_closed_status_maps_to_code_2():
    assert to_status_code(door_status(door_position.CLOSED)) == 2


def test_opening_and_pending_statuses_map_to_code_3():
    assert to_status_code(door_status(door_position.OPENING)) == 3
    assert to_status_code(door_status(door_position.OPEN_PENDING)) == 3


def test_closing_and_pending_statuses_map_to_code_4():
    assert to_status_code(door_status(door_position.CLOSING)) == 4
    assert to_status_code(door_status(door_position.CLOSE_PENDING)) == 4


def test_fault_maps_to_code_6():
    assert to_status_code(door_status(door_position.OPEN, fault="jammed")) == 6


def test_missing_diagnostics_publish_sensible_defaults():
    published = []
    publisher = DoorMqttPublisher(_topics(), _collect(published))

    asyncio.run(publisher.publish_status(door_status(door_position.UNKNOWN)))

    assert published == [
        ("base/chicken-door/status", "unknown", True),
        ("base/chicken-door/status_code", "0", True),
        ("base/chicken-door/fault", "none", True),
        ("base/chicken-door/connected", "1", True),
        ("base/chicken-door/battery", "100", True),
        ("base/chicken-door/light_level", "0", True),
    ]


def test_fake_publish_can_collect_topic_and_payload_only():
    published = []

    async def publish(topic, payload):
        published.append((topic, payload))

    publisher = DoorMqttPublisher(_topics(), publish)

    asyncio.run(publisher.publish_status(door_status(door_position.OPEN)))

    assert published[0] == ("base/chicken-door/status", "open")


def _topics() -> DoorMqttTopics:
    return DoorMqttTopics(
        command="base/chicken-door/command",
        status="base/chicken-door/status",
        status_code="base/chicken-door/status_code",
        fault="base/chicken-door/fault",
        connected="base/chicken-door/connected",
        battery="base/chicken-door/battery",
        light_level="base/chicken-door/light_level",
    )


def _collect(published):
    async def publish(topic, payload, retain=False):
        published.append((topic, payload, retain))

    return publish
