from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from smart_home_contracts.chicken_thread.BoundingBox import BoundingBox


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: BoundingBox | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Detection:
        box_data = data.get("box")
        return cls(
            label=str(data["label"]),
            confidence=float(data["confidence"]),
            box=BoundingBox.from_mapping(box_data) if box_data else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "box": self.box.to_dict() if self.box else None,
        }
