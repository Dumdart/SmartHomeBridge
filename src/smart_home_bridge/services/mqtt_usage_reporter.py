from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

PublishFunction = Callable[..., Awaitable[None] | None]
logger = logging.getLogger(__name__)


class MqttUsageReporter:
    def __init__(self, publish: PublishFunction, base_topic: str):
        self.publish = publish
        self.base_topic = base_topic.rstrip("/")

    async def report_chicken_door(
        self,
        command: str,
        success: bool,
        position: str | None = None,
    ) -> None:
        await self._publish(
            "chicken-door",
            {
                "event": "chicken_door_command",
                "command": command,
                "success": success,
                "position": position,
            },
        )

    async def report_camera_inference(
        self,
        source: str | None,
        success: bool,
        level: str | None = None,
        score: float | None = None,
        detection_count: int | None = None,
    ) -> None:
        await self._publish(
            "camera-inference",
            {
                "event": "camera_inference",
                "source": source,
                "success": success,
                "level": level,
                "score": score,
                "detection_count": detection_count,
            },
        )

    async def _publish(self, topic_name: str, event: dict[str, Any]) -> None:
        event["timestamp"] = datetime.now(UTC).isoformat()
        payload = json.dumps(event, separators=(",", ":"))
        topic = f"{self.base_topic}/usage/{topic_name}"

        try:
            if _accepts_retain(self.publish):
                result = self.publish(topic, payload, retain=False)
            else:
                result = self.publish(topic, payload)

            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Failed to publish MQTT usage event.")


def _accepts_retain(publish: PublishFunction) -> bool:
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
