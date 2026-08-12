from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from smart_home_bridge.bridge_devices.chicken_door.chicken_door import door_position
from smart_home_bridge.bridge_devices.chicken_door.door_status import door_status

DoorPublishFunction = Callable[..., Awaitable[None] | None]


@dataclass(frozen=True)
class DoorMqttTopics:
    command: str
    status: str
    status_code: str
    fault: str
    connected: str
    battery: str
    light_level: str
    usage: str


class DoorMqttPublisher:
    def __init__(
        self,
        topics: DoorMqttTopics,
        publish: DoorPublishFunction,
        retain: bool = True,
    ):
        self.topics = topics
        self.publish = publish
        self.retain = retain

    async def publish_status(self, status: door_status) -> None:
        messages = (
            (self.topics.status, status.position.value),
            (self.topics.status_code, str(to_status_code(status))),
            (self.topics.fault, status.fault or "none"),
            (self.topics.connected, "1" if _default_bool(status.connected, True) else "0"),
            (self.topics.battery, str(_bounded_percent(status.battery_level, 100))),
            (self.topics.light_level, str(_bounded_percent(status.light_level, 0))),
        )

        for topic, payload in messages:
            await self._publish(topic, payload)

    async def _publish(self, topic: str, payload: str) -> None:
        if _accepts_retain(self.publish):
            result = self.publish(topic, payload, retain=self.retain)
        else:
            result = self.publish(topic, payload)

        if inspect.isawaitable(result):
            await result


def to_status_code(status: door_status) -> int:
    if status.fault and status.fault != "none":
        return 6

    if status.position == door_position.OPEN:
        return 1
    if status.position == door_position.CLOSED:
        return 2
    if status.position in {door_position.OPENING, door_position.OPEN_PENDING}:
        return 3
    if status.position in {door_position.CLOSING, door_position.CLOSE_PENDING}:
        return 4
    if status.position == door_position.STOPPING:
        return 5
    return 0


def _bounded_percent(value: int | None, default: int) -> int:
    if value is None:
        return default
    return max(0, min(100, value))


def _default_bool(value: bool | None, default: bool) -> bool:
    if value is None:
        return default
    return value


def _accepts_retain(publish: DoorPublishFunction) -> bool:
    try:
        parameters = inspect.signature(publish).parameters.values()
    except (TypeError, ValueError):
        return True

    for parameter in parameters:
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            return True
        if parameter.name == "retain":
            return True
    return False
