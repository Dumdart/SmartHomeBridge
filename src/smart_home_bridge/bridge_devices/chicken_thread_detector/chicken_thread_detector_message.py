from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.models import DetectionFrame


@dataclass(frozen=True)
class chicken_thread_detector_message:
    topic: str
    payload: str
    parsed_payload: dict[str, Any] | None = None

    @classmethod
    def from_mqtt_payload(cls, topic: str, payload: bytes) -> chicken_thread_detector_message:
        decoded_payload = payload.decode().strip()
        parsed_payload = None

        if decoded_payload.startswith("{"):
            parsed = json.loads(decoded_payload)
            if isinstance(parsed, dict):
                parsed_payload = parsed

        return cls(topic, decoded_payload, parsed_payload)

    async def handle(self, controller: chicken_thread_detector_controller):
        print(f"Received message on topic {self.topic}: {self.payload}")

        if self.parsed_payload is not None:
            if "detections" in self.parsed_payload:
                frame = DetectionFrame.from_mapping(self.parsed_payload)
                return await controller.score_frame(frame)

            return None

        return await controller.excecute_command(self.payload)


async def handle_chicken_thread_detector_mqtt_message(
    topic: str,
    payload: bytes,
    controller: chicken_thread_detector_controller,
):
    try:
        message = chicken_thread_detector_message.from_mqtt_payload(topic, payload)
        return await message.handle(controller)
    except Exception as e:
        print(f"Message is not a detector payload or command: {e}")
