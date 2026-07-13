from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml


TRAINING_CLASS_NAMES = (
    "chicken",
    "other_poultry",
    "rodent",
    "fox",
    "cat",
    "dog",
    "bird_of_prey",
    "other_bird",
    "person",
)

RUNTIME_CLASS_NAMES = (
    "chicken",
    "other_poultry",
    "person",
    "cat",
    "dog",
    "wild_mammal_threat",
    "rodent",
    "bird",
)


def load_class_mapping(path: Path) -> dict[str, str]:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapping = values.get("training_to_runtime")
    if not isinstance(mapping, Mapping):
        raise ValueError(f"{path} must define training_to_runtime")

    clean_mapping = {str(name): str(label) for name, label in mapping.items()}
    if set(clean_mapping) != set(TRAINING_CLASS_NAMES):
        raise ValueError(
            "Class mapping must define exactly these training classes: "
            f"{', '.join(TRAINING_CLASS_NAMES)}"
        )
    unknown_runtime_labels = set(clean_mapping.values()) - set(RUNTIME_CLASS_NAMES)
    if unknown_runtime_labels:
        raise ValueError(
            "Class mapping contains unknown runtime labels: "
            f"{', '.join(sorted(unknown_runtime_labels))}"
        )
    return clean_mapping
