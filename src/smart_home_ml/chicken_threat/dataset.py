from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import yaml
from PIL import Image, UnidentifiedImageError

from smart_home_ml.chicken_threat.taxonomy import TRAINING_CLASS_NAMES, load_class_mapping


REQUIRED_METADATA_COLUMNS = {
    "image_path",
    "label_path",
    "source",
    "capture_group",
    "lighting",
    "split",
}
VALID_SPLITS = ("train", "valid", "test")


class DatasetValidationError(ValueError):
    """Raised when source data cannot safely produce a training dataset."""


@dataclass(frozen=True)
class SourceRecord:
    image_path: Path
    label_path: Path
    source: str
    capture_group: str
    lighting: str
    split: str
    captured_at: str | None = None


@dataclass(frozen=True)
class DatasetValidationReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    split_images: dict[str, int]
    split_objects: dict[str, int]
    class_objects: dict[str, int]
    lighting_images: dict[str, int]

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "split_images": self.split_images,
            "split_objects": self.split_objects,
            "class_objects": self.class_objects,
            "lighting_images": self.lighting_images,
        }


def load_source_metadata(path: Path) -> list[SourceRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DatasetValidationError(f"Metadata file is empty: {path}")
        missing = REQUIRED_METADATA_COLUMNS - set(reader.fieldnames)
        if missing:
            raise DatasetValidationError(
                f"Metadata file is missing columns: {', '.join(sorted(missing))}"
            )
        records = []
        for line_number, row in enumerate(reader, start=2):
            split = (row.get("split") or "").strip().lower()
            if split not in VALID_SPLITS:
                raise DatasetValidationError(
                    f"Metadata row {line_number} has invalid split '{split}'"
                )
            records.append(
                SourceRecord(
                    image_path=_resolve_source_path(path, row["image_path"]),
                    label_path=_resolve_source_path(path, row["label_path"]),
                    source=(row["source"] or "").strip(),
                    capture_group=(row["capture_group"] or "").strip(),
                    lighting=(row["lighting"] or "unknown").strip().lower(),
                    split=split,
                    captured_at=(row.get("captured_at") or "").strip() or None,
                )
            )
    if not records:
        raise DatasetValidationError(f"Metadata file has no image records: {path}")
    return records


def validate_source_records(records: list[SourceRecord]) -> DatasetValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    split_images = {split: 0 for split in VALID_SPLITS}
    split_objects = {split: 0 for split in VALID_SPLITS}
    class_objects = {name: 0 for name in TRAINING_CLASS_NAMES}
    lighting_images: dict[str, int] = {}
    group_splits: dict[str, set[str]] = {}
    hash_splits: dict[str, set[str]] = {}
    hash_count: dict[str, int] = {}

    for record in records:
        split_images[record.split] += 1
        lighting_images[record.lighting] = lighting_images.get(record.lighting, 0) + 1
        if not record.source:
            errors.append(f"{record.image_path}: source is required")
        if not record.capture_group:
            errors.append(f"{record.image_path}: capture_group is required")
        group_splits.setdefault(record.capture_group, set()).add(record.split)
        if not record.image_path.is_file():
            errors.append(f"Missing image: {record.image_path}")
            continue
        if not record.label_path.is_file():
            errors.append(f"Missing label: {record.label_path}")
            continue
        try:
            with Image.open(record.image_path) as image:
                image.verify()
        except (OSError, UnidentifiedImageError) as exc:
            errors.append(f"Invalid image {record.image_path}: {exc}")
            continue
        image_hash = _sha256(record.image_path)
        hash_splits.setdefault(image_hash, set()).add(record.split)
        hash_count[image_hash] = hash_count.get(image_hash, 0) + 1
        try:
            object_count, labels = _validate_yolo_label(record.label_path)
        except DatasetValidationError as exc:
            errors.append(str(exc))
            continue
        split_objects[record.split] += object_count
        for label in labels:
            class_objects[TRAINING_CLASS_NAMES[label]] += 1
        if object_count == 0:
            warnings.append(f"Empty label file: {record.label_path}")

    for group, splits in sorted(group_splits.items()):
        if len(splits) > 1:
            errors.append(
                f"Capture group '{group}' appears in multiple splits: {', '.join(sorted(splits))}"
            )
    for image_hash, splits in sorted(hash_splits.items()):
        if len(splits) > 1:
            errors.append(
                "Duplicate image appears in multiple splits: "
                f"{image_hash[:12]} ({', '.join(sorted(splits))})"
            )
        elif hash_count[image_hash] > 1:
            warnings.append(f"Duplicate image in {next(iter(splits))}: {image_hash[:12]}")
    for split, count in split_images.items():
        if count == 0:
            errors.append(f"Dataset has no {split} images")
    if not any(name in {"day", "night"} for name in lighting_images):
        warnings.append("No explicit day/night lighting metadata is available")

    return DatasetValidationReport(
        errors=tuple(errors),
        warnings=tuple(warnings),
        split_images=split_images,
        split_objects=split_objects,
        class_objects=class_objects,
        lighting_images=lighting_images,
    )


def build_dataset(
    metadata_path: Path,
    output_dir: Path,
    class_mapping_path: Path,
    dataset_version: str,
    sample_limit: int = 24,
    dataset_config_path: Path | None = None,
) -> Path:
    if dataset_config_path is not None:
        config = yaml.safe_load(dataset_config_path.read_text(encoding="utf-8")) or {}
        if config.get("version") != dataset_version:
            raise DatasetValidationError("Dataset version does not match dataset configuration")
        if tuple(config.get("class_names", ())) != TRAINING_CLASS_NAMES:
            raise DatasetValidationError("Dataset configuration has an incompatible class taxonomy")
    records = load_source_metadata(metadata_path)
    report = validate_source_records(records)
    if not report.valid:
        raise DatasetValidationError("\n".join(report.errors))
    load_class_mapping(class_mapping_path)

    dataset_root = output_dir / dataset_version
    if dataset_root.exists():
        shutil.rmtree(dataset_root)
    for split in VALID_SPLITS:
        (dataset_root / split / "images").mkdir(parents=True)
        (dataset_root / split / "labels").mkdir(parents=True)

    manifest_records = []
    for record in sorted(records, key=lambda value: (value.split, str(value.image_path))):
        content_hash = _sha256(record.image_path)
        target_stem = f"{content_hash[:16]}_{record.image_path.stem}"
        target_image = dataset_root / record.split / "images" / (
            target_stem + record.image_path.suffix.lower()
        )
        target_label = dataset_root / record.split / "labels" / f"{target_stem}.txt"
        shutil.copy2(record.image_path, target_image)
        shutil.copy2(record.label_path, target_label)
        manifest_records.append(
            {
                "image": target_image.relative_to(dataset_root).as_posix(),
                "label": target_label.relative_to(dataset_root).as_posix(),
                "sha256": content_hash,
                "source": record.source,
                "capture_group": record.capture_group,
                "lighting": record.lighting,
                "split": record.split,
                "captured_at": record.captured_at,
            }
        )

    data_yaml = {
        "path": ".",
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "names": list(TRAINING_CLASS_NAMES),
    }
    (dataset_root / "data.yaml").write_text(
        yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8"
    )
    manifest = {
        "dataset_version": dataset_version,
        "metadata_sha256": _sha256(metadata_path),
        "class_mapping_sha256": _sha256(class_mapping_path),
        "class_names": list(TRAINING_CLASS_NAMES),
        "validation": report.to_dict(),
        "records": manifest_records,
    }
    _write_json(dataset_root / "dataset_manifest.json", manifest)
    _write_json(dataset_root / "validation.json", report.to_dict())
    _write_inspection_report(dataset_root, report)
    _write_inspection_bundle(dataset_root, sample_limit)
    _write_deterministic_archive(dataset_root)
    return dataset_root


def inspect_dataset(dataset_root: Path, output_dir: Path | None = None) -> DatasetValidationReport:
    manifest_path = dataset_root / "dataset_manifest.json"
    if not manifest_path.is_file():
        raise DatasetValidationError(f"Missing dataset manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = [
        SourceRecord(
            image_path=dataset_root / item["image"],
            label_path=dataset_root / item["label"],
            source=item["source"],
            capture_group=item["capture_group"],
            lighting=item["lighting"],
            split=item["split"],
            captured_at=item.get("captured_at"),
        )
        for item in manifest["records"]
    ]
    report = validate_source_records(records)
    target = output_dir or dataset_root
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "validation.json", report.to_dict())
    _write_inspection_report(target, report)
    return report


def _resolve_source_path(metadata_path: Path, value: str) -> Path:
    candidate = Path(value.strip()).expanduser()
    return candidate if candidate.is_absolute() else (metadata_path.parent / candidate).resolve()


def _validate_yolo_label(path: Path) -> tuple[int, list[int]]:
    labels = []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return 0, labels
    for line_number, line in enumerate(content.splitlines(), start=1):
        values = line.split()
        if len(values) != 5:
            raise DatasetValidationError(f"{path}:{line_number} must contain five YOLO values")
        try:
            class_id = int(values[0])
            coordinates = [float(value) for value in values[1:]]
        except ValueError as exc:
            raise DatasetValidationError(f"{path}:{line_number} contains non-numeric data") from exc
        if class_id < 0 or class_id >= len(TRAINING_CLASS_NAMES):
            raise DatasetValidationError(f"{path}:{line_number} has unknown class id {class_id}")
        x_center, y_center, width, height = coordinates
        if not 0 <= x_center <= 1 or not 0 <= y_center <= 1 or not 0 < width <= 1 or not 0 < height <= 1:
            raise DatasetValidationError(f"{path}:{line_number} has invalid normalized coordinates")
        labels.append(class_id)
    return len(labels), labels


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_inspection_report(dataset_root: Path, report: DatasetValidationReport) -> None:
    rows = "".join(
        f"<tr><th>{name}</th><td>{count}</td></tr>"
        for name, count in sorted(report.class_objects.items())
    )
    errors = "<br>".join(report.errors) or "None"
    warnings = "<br>".join(report.warnings) or "None"
    dataset_root.joinpath("inspection_report.html").write_text(
        "<!doctype html><html><body>"
        "<h1>Chicken-threat dataset inspection</h1>"
        f"<p>Valid: {report.valid}</p><h2>Errors</h2><p>{errors}</p>"
        f"<h2>Warnings</h2><p>{warnings}</p><h2>Objects by class</h2>"
        f"<table>{rows}</table></body></html>",
        encoding="utf-8",
    )


def _write_inspection_bundle(dataset_root: Path, sample_limit: int) -> None:
    bundle_root = dataset_root / "inspection"
    bundle_root.mkdir()
    for name in ("dataset_manifest.json", "validation.json", "inspection_report.html"):
        shutil.copy2(dataset_root / name, bundle_root / name)
    images = []
    for split in VALID_SPLITS:
        images.extend(sorted((dataset_root / split / "images").iterdir()))
    for image_path in images[:sample_limit]:
        sample_dir = bundle_root / "samples" / image_path.parent.parent.name
        sample_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, sample_dir / image_path.name)
    _write_deterministic_archive(bundle_root, dataset_root / "inspection_bundle.zip")


def _write_deterministic_archive(source_dir: Path, destination: Path | None = None) -> Path:
    destination = destination or source_dir.parent / f"{source_dir.name}.zip"
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(candidate for candidate in source_dir.rglob("*") if candidate.is_file()):
            info = ZipInfo(path.relative_to(source_dir).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return destination
