from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from smart_home_contracts.chicken_thread.Detection import Detection


@dataclass(frozen=True)
class DetectionFrame:
    detections: tuple[Detection, ...] = field(default_factory=tuple)
    source: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> DetectionFrame:
        return cls(
            detections=tuple(
                Detection.from_mapping(item) for item in data.get("detections", [])
            ),
            source=data.get("source"),
        )

    @classmethod
    def from_json(cls, payload: str) -> DetectionFrame:
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ValueError("Detection payload must be a JSON object.")

        return cls.from_mapping(parsed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detections": [detection.to_dict() for detection in self.detections],
            "source": self.source,
        }
