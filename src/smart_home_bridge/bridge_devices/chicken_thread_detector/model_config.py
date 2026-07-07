from dataclasses import dataclass, field


MODEL_CLASS_NAMES = (
    "chicken",
    "other_poultry",
    "person",
    "cat",
    "dog",
    "wild_mammal_threat",
    "rodent",
    "bird",
)

LABEL_ALIASES = {
    "fox": "wild_mammal_threat",
    "marten": "wild_mammal_threat",
    "weasel": "wild_mammal_threat",
    "marten_weasel": "wild_mammal_threat",
    "other_bird": "bird",
    "bird_of_prey": "bird",
}

RISK_BY_LABEL = {
    "chicken": 0.0,
    "other_poultry": 0.0,
    "person": 0.0,
    "cat": 0.55,
    "dog": 0.75,
    "wild_mammal_threat": 0.95,
    "rodent": 0.65,
    "bird": 0.6,
}


@dataclass(frozen=True)
class ChickenThreadScoringConfig:
    class_names: tuple[str, ...]
    risk_by_label: dict[str, float]
    label_aliases: dict[str, str] = field(default_factory=dict)
    confidence_threshold: float = 0.35
    medium_threshold: float = 0.4
    high_threshold: float = 0.7
    critical_threshold: float = 0.9

    def normalized_label(self, label: str) -> str:
        clean_label = label.strip().lower()
        return self.label_aliases.get(clean_label, clean_label)


def default_model_config(
    confidence_threshold: float = 0.35,
) -> ChickenThreadScoringConfig:
    return ChickenThreadScoringConfig(
        class_names=MODEL_CLASS_NAMES,
        risk_by_label=RISK_BY_LABEL,
        label_aliases=LABEL_ALIASES,
        confidence_threshold=confidence_threshold,
        medium_threshold=0.4,
        high_threshold=0.7,
        critical_threshold=0.9,
    )

__all__ = [
    "LABEL_ALIASES",
    "MODEL_CLASS_NAMES",
    "RISK_BY_LABEL",
    "ChickenThreadScoringConfig",
    "default_model_config",
]
