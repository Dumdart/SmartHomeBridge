from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float
    normalized: bool = True

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> BoundingBox:
        return cls(
            left=float(data["left"]),
            top=float(data["top"]),
            right=float(data["right"]),
            bottom=float(data["bottom"]),
            normalized=bool(data.get("normalized", True)),
        )

    def to_dict(self) -> dict[str, float | bool]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "normalized": self.normalized,
        }


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


@dataclass(frozen=True)
class DetectionFrame:
    detections: tuple[Detection, ...] = field(default_factory=tuple)
    source: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> DetectionFrame:
        return cls(
            detections=tuple(Detection.from_mapping(item) for item in data.get("detections", [])),
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


@dataclass(frozen=True)
class DangerAssessment:
    level: ThreatLevel
    score: float
    triggering_detections: tuple[Detection, ...] = field(default_factory=tuple)
    detection_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "score": self.score,
            "detection_count": self.detection_count,
            "triggering_detections": [
                detection.to_dict() for detection in self.triggering_detections
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


@dataclass(frozen=True)
class ChickenThreadModelConfig:
    model_path: str
    class_names: tuple[str, ...]
    risk_by_label: dict[str, float]
    label_aliases: dict[str, str] = field(default_factory=dict)
    confidence_threshold: float = 0.35
    image_size: int = 640
    medium_threshold: float = 0.4
    high_threshold: float = 0.7
    critical_threshold: float = 0.9

    def normalized_label(self, label: str) -> str:
        clean_label = label.strip().lower()
        return self.label_aliases.get(clean_label, clean_label)
