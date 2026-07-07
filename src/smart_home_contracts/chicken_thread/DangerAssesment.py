from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from smart_home_contracts.chicken_thread.Detection import Detection
from smart_home_contracts.chicken_thread.ThreadLevel import ThreatLevel


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
