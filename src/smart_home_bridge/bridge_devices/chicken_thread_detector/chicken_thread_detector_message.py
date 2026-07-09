from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_contracts.chicken_thread import DetectionFrame

MAX_DETECTOR_PAYLOAD_BYTES = 200_000
MAX_DETECTIONS_PER_MESSAGE = 250
MAX_DETECTION_LABEL_LENGTH = 80


@dataclass(frozen=True)
class chicken_thread_detector_message:
    topic: str
    payload: str
    parsed_payload: dict[str, Any] | None = None

    @classmethod
    def from_mqtt_payload(cls, topic: str, payload: bytes) -> chicken_thread_detector_message:
        if len(payload) > MAX_DETECTOR_PAYLOAD_BYTES:
            raise ValueError(
                f"Detector payload exceeds {MAX_DETECTOR_PAYLOAD_BYTES} bytes"
            )

        decoded_payload = payload.decode().strip()
        parsed_payload = None

        if decoded_payload.startswith("{"):
            parsed = json.loads(decoded_payload)
            if isinstance(parsed, dict):
                _validate_detection_payload(parsed)
                parsed_payload = parsed

        return cls(topic, decoded_payload, parsed_payload)

    async def handle(self, controller: chicken_thread_detector_controller):
        print(f"Received message on topic {self.topic}: {len(self.payload)} bytes")

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
    message = chicken_thread_detector_message.from_mqtt_payload(topic, payload)
    return await message.handle(controller)


def _validate_detection_payload(payload: dict[str, Any]):
    detections = payload.get("detections")
    if detections is None:
        return

    if not isinstance(detections, list):
        raise ValueError("Detector detections must be a JSON array")

    if len(detections) > MAX_DETECTIONS_PER_MESSAGE:
        raise ValueError(
            f"Detector payload contains more than {MAX_DETECTIONS_PER_MESSAGE} detections"
        )

    for detection in detections:
        if not isinstance(detection, dict):
            raise ValueError("Detector detection entries must be JSON objects")

        label = str(detection.get("label", ""))
        if len(label) > MAX_DETECTION_LABEL_LENGTH:
            raise ValueError(
                f"Detector label exceeds {MAX_DETECTION_LABEL_LENGTH} characters"
            )
