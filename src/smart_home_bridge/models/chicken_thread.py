from dataclasses import dataclass, field

from smart_home_contracts.chicken_thread import (
    BoundingBox,
    DangerAssessment,
    Detection,
    DetectionFrame,
    ThreatLevel,
)


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
