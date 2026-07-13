from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import shutil
import time
import traceback
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote, urlparse

import yaml
from PIL import Image

from smart_home_ml.chicken_threat.dataset import VALID_SPLITS
from smart_home_ml.chicken_threat.taxonomy import TRAINING_CLASS_NAMES


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
METADATA_COLUMNS = (
    "image_path",
    "label_path",
    "source",
    "capture_group",
    "lighting",
    "split",
    "captured_at",
)


class DatasetDownloadError(RuntimeError):
    """Raised when a requested dataset source cannot be acquired safely."""


@dataclass(frozen=True)
class DownloadRecord:
    image_path: Path
    label_path: Path
    source: str
    capture_group: str
    lighting: str
    split: str
    captured_at: str | None = None

    def metadata_row(self, workspace: Path) -> dict[str, str]:
        return {
            "image_path": self.image_path.relative_to(workspace).as_posix(),
            "label_path": self.label_path.relative_to(workspace).as_posix(),
            "source": self.source,
            "capture_group": self.capture_group,
            "lighting": self.lighting,
            "split": self.split,
            "captured_at": self.captured_at or "",
        }


def default_download_config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "ml/chicken_threat/configs/download_sources.yaml"


def download_datasets(
    workspace: Path,
    config_path: Path | None = None,
    source_names: Iterable[str] = (),
    refresh_sources: Iterable[str] = (),
    refresh_all: bool = False,
    verbose: bool = False,
) -> Path:
    workspace = workspace.resolve()
    config_path = (config_path or default_download_config_path()).resolve()
    config = _load_config(config_path)
    sources = config["sources"]
    selected_names = tuple(source_names) or tuple(
        name for name, value in sources.items() if value.get("enabled", True)
    )
    _validate_source_names(selected_names, sources, "--source")
    refresh_names = set(refresh_sources)
    _validate_source_names(refresh_names, sources, "--refresh")
    if refresh_all:
        refresh_names.update(selected_names)
    if refresh_names - set(selected_names):
        raise DatasetDownloadError("--refresh sources must also be selected with --source")
    _validate_roboflow_credentials(selected_names, sources)

    for directory in (workspace / "raw", workspace / "cache", workspace / "manifests"):
        directory.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(selected_names)} source(s) into {workspace}")
    records: list[DownloadRecord] = []
    reports: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, name in enumerate(selected_names, start=1):
        source = sources[name]
        started = time.perf_counter()
        print(f"[{index}/{len(selected_names)}] {name} ({source.get('type', 'unknown')}): starting")
        try:
            source_records, report = _download_source(
                name=name,
                source=source,
                workspace=workspace,
                seed=int(config["seed"]),
                refresh=name in refresh_names,
            )
            records.extend(source_records)
            report["duration_seconds"] = round(time.perf_counter() - started, 2)
            reports.append(report)
            print(
                f"[{index}/{len(selected_names)}] {name}: {report['status']} "
                f"({len(source_records)} records, {report['duration_seconds']:.2f}s)"
            )
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            failure = {
                "name": name,
                "status": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "duration_seconds": round(time.perf_counter() - started, 2),
            }
            reports.append(failure)
            print(f"[{index}/{len(selected_names)}] {name}: FAILED after {failure['duration_seconds']:.2f}s: {exc}")
            if verbose:
                print(failure["traceback"].rstrip())

    report_path = workspace / "download_report.json"
    report_path.write_text(
        json.dumps(
            {
                "config": config_path.as_posix(),
                "selected_sources": list(selected_names),
                "refresh_sources": sorted(refresh_names),
                "source_definitions": {name: sources[name] for name in selected_names},
                "sources": reports,
                "record_count": len(records),
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if errors:
        raise DatasetDownloadError(
            "Dataset download failed. See " + str(report_path) + "\n" + "\n".join(errors)
        )
    if not records:
        raise DatasetDownloadError(f"No usable records were downloaded. See {report_path}")

    metadata_path = workspace / "source_metadata.csv"
    written, duplicates = _write_source_metadata(metadata_path, workspace, records)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["metadata_path"] = metadata_path.as_posix()
    report["metadata_record_count"] = written
    report["duplicate_images_skipped"] = duplicates
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Download metadata written: {metadata_path} ({written} records, {duplicates} duplicates skipped)")
    return metadata_path


def _load_config(path: Path) -> dict[str, Any]:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(values, dict) or not isinstance(values.get("sources"), dict):
        raise DatasetDownloadError(f"{path} must define a sources mapping")
    if tuple(values.get("canonical_classes", ())) != TRAINING_CLASS_NAMES:
        raise DatasetDownloadError(f"{path} has an incompatible canonical class taxonomy")
    if not isinstance(values.get("seed"), int):
        raise DatasetDownloadError(f"{path} must define an integer seed")
    return values


def _validate_source_names(names: Iterable[str], sources: Mapping[str, Any], option: str) -> None:
    unknown = sorted(set(names) - set(sources))
    if unknown:
        raise DatasetDownloadError(f"{option} names are unknown: {', '.join(unknown)}")


def _validate_roboflow_credentials(names: Iterable[str], sources: Mapping[str, Any]) -> None:
    import os

    if any(sources[name].get("type") == "roboflow_yolo" for name in names) and not os.getenv(
        "ROBOFLOW_API_KEY"
    ):
        raise DatasetDownloadError("Set ROBOFLOW_API_KEY before downloading Roboflow sources")


def _download_source(
    name: str,
    source: Mapping[str, Any],
    workspace: Path,
    seed: int,
    refresh: bool,
) -> tuple[list[DownloadRecord], dict[str, Any]]:
    manifest_path = workspace / "manifests" / f"{name}.json"
    if not refresh:
        cached = _load_complete_manifest(manifest_path, workspace)
        if cached is not None:
            print(f"  Reusing complete manifest: {manifest_path}")
            return cached, {"name": name, "status": "cached", "records": len(cached)}

    source_root = workspace / "raw" / name
    if refresh:
        print(f"  Refreshing source output: {source_root}")
        shutil.rmtree(source_root, ignore_errors=True)
        manifest_path.unlink(missing_ok=True)
    source_type = str(source.get("type", ""))
    if source_type == "unsupported":
        report = {
            "name": name,
            "status": "skipped",
            "reason": str(source.get("skip_reason", "Unsupported source")),
            "records": 0,
        }
        _write_manifest(manifest_path, workspace, [], report)
        return [], report
    if source_type == "roboflow_yolo":
        records, details = _download_roboflow_yolo(name, source, workspace, source_root)
    elif source_type == "open_images":
        records, details = _download_open_images(name, source, workspace, source_root, seed)
    elif source_type == "lila_coco":
        records, details = _download_lila_coco(name, source, workspace, source_root, seed)
    else:
        raise DatasetDownloadError(f"Unsupported downloader type {source_type!r}")
    report = {"name": name, "status": "downloaded", "records": len(records), **details}
    _write_manifest(manifest_path, workspace, records, report)
    return records, report


def _load_complete_manifest(path: Path, workspace: Path) -> list[DownloadRecord] | None:
    if not path.is_file():
        return None
    values = json.loads(path.read_text(encoding="utf-8"))
    if values.get("status") == "skipped":
        return []
    records = [_record_from_dict(item, workspace) for item in values.get("records", [])]
    if records and all(record.image_path.is_file() and record.label_path.is_file() for record in records):
        return records
    return None


def _write_manifest(
    path: Path, workspace: Path, records: list[DownloadRecord], report: Mapping[str, Any]
) -> None:
    values = {
        "status": report["status"],
        "report": dict(report),
        "records": [record.metadata_row(workspace) for record in records],
    }
    path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record_from_dict(value: Mapping[str, Any], workspace: Path) -> DownloadRecord:
    return DownloadRecord(
        image_path=workspace / str(value["image_path"]),
        label_path=workspace / str(value["label_path"]),
        source=str(value["source"]),
        capture_group=str(value["capture_group"]),
        lighting=str(value["lighting"]),
        split=str(value["split"]),
        captured_at=str(value["captured_at"]) or None,
    )


def _download_roboflow_yolo(
    name: str, source: Mapping[str, Any], workspace: Path, output_root: Path
) -> tuple[list[DownloadRecord], dict[str, Any]]:
    try:
        from roboflow import Roboflow
    except ImportError as exc:
        raise DatasetDownloadError("Install the ml extra to download Roboflow sources") from exc
    import os

    download_root = workspace / "cache" / "roboflow" / name
    shutil.rmtree(download_root, ignore_errors=True)
    print(
        f"  Roboflow: loading {source['workspace']}/{source['project']} "
        f"(requested version: {source.get('version', 'latest')})"
    )
    rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
    project = rf.workspace(str(source["workspace"])).project(str(source["project"]))
    version_number, version = _resolve_roboflow_version(project, source.get("version"))
    print(f"  Roboflow: downloading YOLOv8 export for version {version_number}")
    download = version.download("yolov8", location=str(download_root), overwrite=True)
    try:
        source_root = _find_yolo_root(Path(download.location))
        print(f"  Roboflow: normalizing export at {source_root}")
        records = _copy_yolo_source(
            source_root=source_root,
            output_root=output_root,
            source_name=name,
            class_map=source.get("class_map", {}),
            keep_empty_images=bool(source.get("keep_empty_images", False)),
        )
    finally:
        shutil.rmtree(download_root, ignore_errors=True)
    return records, {
        "provider": "roboflow",
        "workspace": str(source["workspace"]),
        "project": str(source["project"]),
        "version": version_number,
    }


def _resolve_roboflow_version(project: Any, configured_version: Any) -> tuple[int, Any]:
    if configured_version is not None:
        return int(configured_version), project.version(int(configured_version))
    for number in range(100, 0, -1):
        try:
            return number, project.version(number)
        except RuntimeError as exc:
            if "not found" not in str(exc).lower():
                raise
    raise DatasetDownloadError("No generated Roboflow dataset version was found")


def _find_yolo_root(root: Path) -> Path:
    candidates = [root, *[path.parent for path in root.rglob("data.yaml")]]
    for candidate in candidates:
        if (candidate / "data.yaml").is_file():
            return candidate
    raise DatasetDownloadError(f"No YOLO data.yaml found below {root}")


def _copy_yolo_source(
    source_root: Path,
    output_root: Path,
    source_name: str,
    class_map: Mapping[str, Any],
    keep_empty_images: bool,
) -> list[DownloadRecord]:
    class_names = _load_yolo_class_names(source_root / "data.yaml")
    records: list[DownloadRecord] = []
    for split in VALID_SPLITS:
        image_dir = source_root / split / "images"
        label_dir = source_root / split / "labels"
        images = _image_files(image_dir)
        print(f"  {source_name}: normalizing {split} ({len(images)} images)")
        for image_path in _progress(images, f"{source_name}:{split}", "image"):
            label_path = label_dir / f"{image_path.stem}.txt"
            lines = label_path.read_text(encoding="utf-8").splitlines() if label_path.is_file() else []
            output_lines = []
            for line in lines:
                parsed = _parse_yolo_line(line)
                if parsed is None:
                    continue
                class_id, box = parsed
                if box is None:
                    continue
                if not 0 <= class_id < len(class_names):
                    continue
                canonical = class_map.get(class_names[class_id])
                if canonical not in TRAINING_CLASS_NAMES:
                    continue
                output_lines.append(_format_yolo_line(TRAINING_CLASS_NAMES.index(canonical), box))
            if not output_lines and not keep_empty_images:
                continue
            stem = _slugify(f"{source_name}_{split}_{image_path.stem}")
            destination_image = output_root / split / "images" / f"{stem}{image_path.suffix.lower()}"
            destination_label = output_root / split / "labels" / f"{stem}.txt"
            destination_image.parent.mkdir(parents=True, exist_ok=True)
            destination_label.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, destination_image)
            destination_label.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")
            records.append(
                DownloadRecord(
                    destination_image,
                    destination_label,
                    source_name,
                    f"{source_name}:{split}:{image_path.stem}",
                    "unknown",
                    split,
                )
            )
    return records


def _load_yolo_class_names(path: Path) -> list[str]:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    names = values.get("names", [])
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda value: int(value))]
    if isinstance(names, list):
        return [str(name) for name in names]
    raise DatasetDownloadError(f"{path} has no supported YOLO names mapping")


def _download_open_images(
    name: str,
    source: Mapping[str, Any],
    workspace: Path,
    output_root: Path,
    seed: int,
) -> tuple[list[DownloadRecord], dict[str, Any]]:
    try:
        import fiftyone.zoo as foz
    except ImportError as exc:
        raise DatasetDownloadError("Install the ml extra to download Open Images sources") from exc
    split_map = {"train": "train", "valid": "validation", "test": "test"}
    records: list[DownloadRecord] = []
    seen_filepaths: set[Path] = set()
    for split, open_images_split in split_map.items():
        targets = source["target_images"].get(split, {})
        for source_class, max_samples in targets.items():
            canonical = source.get("class_map", {}).get(source_class)
            if canonical not in TRAINING_CLASS_NAMES or int(max_samples) <= 0:
                continue
            print(f"  Open Images: {split}/{source_class} (up to {max_samples} images)")
            dataset = foz.load_zoo_dataset(
                "open-images-v7",
                split=open_images_split,
                label_types=["detections"],
                classes=[source_class],
                max_samples=int(max_samples),
                shuffle=True,
                seed=seed,
                only_matching=True,
                dataset_name=f"chicken-threat-{split}-{_slugify(source_class)}",
                overwrite=True,
            )
            detection_field = _fiftyone_detection_field(dataset)
            for sample in _progress(dataset, f"open_images:{split}:{source_class}", "image"):
                image_path = Path(sample.filepath).resolve()
                if image_path in seen_filepaths:
                    continue
                detections = getattr(sample[detection_field], "detections", []) if sample[detection_field] else []
                output_lines = []
                for detection in detections:
                    if detection.label != source_class:
                        continue
                    box = _fiftyone_box_to_yolo(detection.bounding_box)
                    if box is not None:
                        output_lines.append(_format_yolo_line(TRAINING_CLASS_NAMES.index(canonical), box))
                if not output_lines:
                    continue
                seen_filepaths.add(image_path)
                sample_id = str(sample.id)
                stem = _slugify(f"{source_class}_{sample_id}")
                destination_image = output_root / split / "images" / f"{stem}{image_path.suffix.lower()}"
                destination_label = output_root / split / "labels" / f"{stem}.txt"
                destination_image.parent.mkdir(parents=True, exist_ok=True)
                destination_label.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image_path, destination_image)
                destination_label.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
                records.append(
                    DownloadRecord(
                        destination_image,
                        destination_label,
                        name,
                        f"{name}:{sample_id}",
                        "unknown",
                        split,
                    )
                )
    return records, {"provider": "fiftyone", "dataset": "open-images-v7"}


def _fiftyone_detection_field(dataset: Any) -> str:
    for field_name, field in dataset.get_field_schema().items():
        document_type = getattr(field, "document_type", None)
        if document_type is not None and document_type.__name__ == "Detections":
            return field_name
    raise DatasetDownloadError("Open Images download has no detections field")


def _download_lila_coco(
    name: str,
    source: Mapping[str, Any],
    workspace: Path,
    output_root: Path,
    seed: int,
) -> tuple[list[DownloadRecord], dict[str, Any]]:
    metadata_url = str(source["metadata_url"])
    metadata_path = workspace / "cache" / name / _cache_name(metadata_url)
    print(f"  LILA: loading metadata from {metadata_url}")
    payload = _download_file(metadata_url, metadata_path)
    metadata = _read_json_payload(payload)
    images = {str(item.get("id")): item for item in metadata.get("images", [])}
    categories = {str(item.get("id")): _normalise_name(item.get("name")) for item in metadata.get("categories", [])}
    annotations_by_image: dict[str, list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    class_map = {_normalise_name(key): value for key, value in source.get("class_map", {}).items()}
    for annotation in metadata.get("annotations", []):
        category_value = (
            annotation.get("category")
            or annotation.get("category_name")
            or annotation.get("label")
            or categories.get(str(annotation.get("category_id")), "")
        )
        if isinstance(category_value, Mapping):
            category_value = category_value.get("name") or category_value.get("label") or ""
        source_class = _normalise_name(category_value)
        canonical = class_map.get(source_class)
        if canonical in TRAINING_CLASS_NAMES and annotation.get("bbox"):
            annotations_by_image[str(annotation.get("image_id"))].append((canonical, annotation))

    candidates = sorted(annotations_by_image.items())
    random.Random(seed).shuffle(candidates)
    print(f"  LILA: {len(candidates)} images have mapped boxed annotations")
    counts: dict[str, Counter[str]] = {split: Counter() for split in VALID_SPLITS}
    records: list[DownloadRecord] = []
    skipped_downloads = 0
    for image_id, annotations in _progress(candidates, f"lila:{name}", "candidate"):
        image = images.get(image_id)
        if image is None:
            continue
        file_name = _coco_file_name(image)
        capture_group = _capture_group(name, image, file_name)
        split = _stable_split(capture_group)
        caps = source.get("object_caps", {}).get(split, {})
        image_counts = Counter(canonical for canonical, _ in annotations)
        if not any(counts[split][canonical] < int(caps.get(canonical, 0)) for canonical in image_counts):
            continue
        suffix = Path(file_name).suffix.lower()
        suffix = suffix if suffix in IMAGE_SUFFIXES else ".jpg"
        stem = _slugify(f"{name}_{Path(file_name).with_suffix('').as_posix()}")
        destination_image = output_root / split / "images" / f"{stem}{suffix}"
        destination_label = output_root / split / "labels" / f"{stem}.txt"
        image_url = str(source["image_base_url"]).rstrip("/") + "/" + quote(file_name.lstrip("/"), safe="/()_.-~")
        try:
            _download_file(image_url, destination_image)
            with Image.open(destination_image) as loaded:
                width, height = loaded.size
        except Exception:
            destination_image.unlink(missing_ok=True)
            skipped_downloads += 1
            continue
        output_lines = []
        written_counts: Counter[str] = Counter()
        for canonical, annotation in annotations:
            box = _coco_box_to_yolo(annotation["bbox"], width, height)
            if box is None:
                continue
            output_lines.append(_format_yolo_line(TRAINING_CLASS_NAMES.index(canonical), box))
            written_counts[canonical] += 1
        if not output_lines:
            destination_image.unlink(missing_ok=True)
            continue
        destination_label.parent.mkdir(parents=True, exist_ok=True)
        destination_label.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
        counts[split].update(written_counts)
        records.append(
            DownloadRecord(
                destination_image,
                destination_label,
                name,
                capture_group,
                "night" if _is_night(image) else "day",
                split,
                _captured_at(image),
            )
        )
    return records, {
        "provider": "lila",
        "metadata_url": metadata_url,
        "skipped_downloads": skipped_downloads,
        "objects_by_split": {split: dict(counter) for split, counter in counts.items()},
    }


def _download_file(url: str, destination: Path) -> Path:
    if destination.is_file() and destination.stat().st_size > 0:
        return destination
    try:
        import requests
    except ImportError as exc:
        raise DatasetDownloadError("Install the ml extra to download remote sources") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _progress(items: Iterable[Any], description: str, unit: str) -> Iterable[Any]:
    try:
        from tqdm.auto import tqdm
    except ImportError:
        return items
    return tqdm(items, desc=description, unit=unit, dynamic_ncols=True, mininterval=0.5)


def _read_json_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = sorted(name for name in archive.namelist() if name.lower().endswith(".json"))
            if not names:
                raise DatasetDownloadError(f"No JSON payload found in {path}")
            return json.loads(archive.read(names[0]).decode("utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def _write_source_metadata(
    path: Path, workspace: Path, records: list[DownloadRecord]
) -> tuple[int, int]:
    rows: list[dict[str, str]] = []
    hashes: set[str] = set()
    duplicates = 0
    for record in sorted(records, key=lambda item: (item.split, item.source, str(item.image_path))):
        digest = _sha256(record.image_path)
        if digest in hashes:
            duplicates += 1
            continue
        hashes.add(digest)
        rows.append(record.metadata_row(workspace))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), duplicates


def _parse_yolo_line(line: str) -> tuple[int, tuple[float, float, float, float]] | None:
    values = line.split()
    if len(values) < 5:
        return None
    try:
        class_id = int(float(values[0]))
        coordinates = [float(value) for value in values[1:]]
    except ValueError:
        return None
    if len(coordinates) == 4:
        return class_id, _clip_yolo_box(coordinates)
    if len(coordinates) < 6 or len(coordinates) % 2:
        return None
    xs, ys = coordinates[0::2], coordinates[1::2]
    return class_id, _clip_yolo_box(
        [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)]
    )


def _clip_yolo_box(values: Iterable[float]) -> tuple[float, float, float, float] | None:
    x_center, y_center, width, height = [float(value) for value in values]
    x_min, y_min = max(0.0, x_center - width / 2), max(0.0, y_center - height / 2)
    x_max, y_max = min(1.0, x_center + width / 2), min(1.0, y_center + height / 2)
    if x_max <= x_min or y_max <= y_min:
        return None
    return ((x_min + x_max) / 2, (y_min + y_max) / 2, x_max - x_min, y_max - y_min)


def _format_yolo_line(class_id: int, box: tuple[float, float, float, float] | None) -> str:
    if box is None:
        raise ValueError("Cannot format an empty bounding box")
    return f"{class_id} " + " ".join(f"{value:.6f}" for value in box)


def _fiftyone_box_to_yolo(values: Iterable[float]) -> tuple[float, float, float, float] | None:
    x_min, y_min, width, height = [float(value) for value in values]
    return _clip_yolo_box((x_min + width / 2, y_min + height / 2, width, height))


def _coco_box_to_yolo(
    values: Iterable[float], image_width: int, image_height: int
) -> tuple[float, float, float, float] | None:
    x_min, y_min, width, height = [float(value) for value in values]
    if image_width <= 0 or image_height <= 0:
        return None
    return _clip_yolo_box(
        ((x_min + width / 2) / image_width, (y_min + height / 2) / image_height, width / image_width, height / image_height)
    )


def _image_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(candidate for candidate in path.iterdir() if candidate.suffix.lower() in IMAGE_SUFFIXES)


def _normalise_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").strip().lower())


def _coco_file_name(image: Mapping[str, Any]) -> str:
    for key in ("file_name", "file", "filepath", "path", "id"):
        if image.get(key):
            return str(image[key]).replace("\\", "/")
    raise DatasetDownloadError(f"COCO image has no file name: {image}")


def _capture_group(name: str, image: Mapping[str, Any], file_name: str) -> str:
    location = image.get("location") or image.get("location_id") or image.get("seq_id")
    return f"{name}:{location}" if location else f"{name}:{file_name}"


def _stable_split(capture_group: str) -> str:
    value = int(hashlib.sha1(capture_group.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "train" if value < 0.8 else "valid" if value < 0.9 else "test"


def _is_night(image: Mapping[str, Any]) -> bool:
    for key in ("is_night", "night", "infrared", "ir", "flash"):
        value = image.get(key)
        if value is True or str(value).strip().lower() in {"true", "1", "yes", "night", "ir", "infrared"}:
            return True
    return any(_night_from_text(image.get(key)) for key in ("datetime", "date_time", "date_captured", "timestamp", "file_name", "id"))


def _night_from_text(value: Any) -> bool:
    match = re.search(r"(?:^|[^0-9])([01][0-9]|2[0-3])[-_:hH]?([0-5][0-9])", str(value or ""))
    return bool(match and (int(match.group(1)) < 6 or int(match.group(1)) >= 20))


def _captured_at(image: Mapping[str, Any]) -> str | None:
    for key in ("datetime", "date_time", "date_captured", "timestamp"):
        if image.get(key):
            return str(image[key])
    return None


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._") or "item"


def _cache_name(url: str) -> str:
    suffix = Path(urlparse(url).path).name or "metadata.json"
    return f"{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}_{suffix}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
