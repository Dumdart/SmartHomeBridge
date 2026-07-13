from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import yaml


MODEL_PACKAGE = "smart_home_inference.models.chicken_thread.model"
MODEL_MANIFEST_NAME = "model_manifest.yaml"
EXPECTED_TRAINING_CLASSES = (
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
EXPECTED_RUNTIME_CLASSES = (
    "chicken",
    "other_poultry",
    "person",
    "cat",
    "dog",
    "wild_mammal_threat",
    "rodent",
    "bird",
)
EXPECTED_CLASS_MAPPING = {
    "chicken": "chicken",
    "other_poultry": "other_poultry",
    "rodent": "rodent",
    "fox": "wild_mammal_threat",
    "cat": "cat",
    "dog": "dog",
    "bird_of_prey": "bird",
    "other_bird": "bird",
    "person": "person",
}


@dataclass(frozen=True)
class ProductionModelManifest:
    model_id: str
    file: str
    sha256: str
    training_classes: tuple[str, ...]
    runtime_classes: tuple[str, ...]
    class_mapping: dict[str, str]
    thresholds: dict[str, float | int]


def default_model_path() -> str:
    manifest = load_production_model_manifest()
    return str(files(MODEL_PACKAGE).joinpath(manifest.file))


def load_production_model_manifest() -> ProductionModelManifest:
    manifest_path = files(MODEL_PACKAGE).joinpath(MODEL_MANIFEST_NAME)
    values = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    required = {"model_id", "file", "sha256", "training_classes", "runtime_classes", "class_mapping", "thresholds"}
    missing = required - set(values)
    if missing:
        raise ValueError(f"Production model manifest is missing: {', '.join(sorted(missing))}")
    manifest = ProductionModelManifest(
        model_id=str(values["model_id"]),
        file=str(values["file"]),
        sha256=str(values["sha256"]),
        training_classes=tuple(str(value) for value in values["training_classes"]),
        runtime_classes=tuple(str(value) for value in values["runtime_classes"]),
        class_mapping={str(key): str(value) for key, value in values["class_mapping"].items()},
        thresholds={str(key): value for key, value in values["thresholds"].items()},
    )
    if manifest.training_classes != EXPECTED_TRAINING_CLASSES:
        raise ValueError("Production model manifest has an incompatible training taxonomy")
    if manifest.runtime_classes != EXPECTED_RUNTIME_CLASSES:
        raise ValueError("Production model manifest has an incompatible runtime taxonomy")
    if manifest.class_mapping != EXPECTED_CLASS_MAPPING:
        raise ValueError("Production model manifest has an incompatible class mapping")
    return manifest


def verify_production_model(path: str | Path) -> ProductionModelManifest:
    manifest = load_production_model_manifest()
    model_path = Path(path)
    expected_path = Path(str(files(MODEL_PACKAGE).joinpath(manifest.file)))
    if model_path.resolve() != expected_path.resolve():
        raise ValueError("Default production model path does not match the model manifest")
    if not model_path.is_file():
        raise FileNotFoundError(f"Production model file is missing: {model_path}")
    actual_sha256 = _sha256(model_path)
    if actual_sha256 != manifest.sha256:
        raise ValueError(
            "Production model checksum does not match model_manifest.yaml; "
            "ensure Git LFS has fetched the approved model."
        )
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
