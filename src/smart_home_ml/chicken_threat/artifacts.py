from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from smart_home_ml.chicken_threat.taxonomy import (
    RUNTIME_CLASS_NAMES,
    TRAINING_CLASS_NAMES,
    load_class_mapping,
)


class PromotionError(ValueError):
    """Raised when a candidate cannot become the approved production model."""


def train_model(dataset_yaml: Path, training_config_path: Path, output_dir: Path) -> Path:
    config = _load_yaml(training_config_path)
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Install the ml dependency group to train a model") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(config["base_weights"]))
    results = model.train(
        data=str(dataset_yaml),
        epochs=int(config["epochs"]),
        imgsz=int(config["image_size"]),
        batch=int(config["batch"]),
        device=config["device"],
        patience=int(config["patience"]),
        cos_lr=bool(config["cos_lr"]),
        close_mosaic=int(config["close_mosaic"]),
        seed=int(config["seed"]),
        project=str(output_dir),
        name=str(config["run_name"]),
    )
    save_dir = Path(getattr(results, "save_dir", output_dir / str(config["run_name"])))
    if not (save_dir / "weights" / "best.pt").is_file():
        raise RuntimeError(f"Training completed without best.pt in {save_dir}")
    return save_dir


def evaluate_model(
    weights_path: Path,
    dataset_yaml: Path,
    class_mapping_path: Path,
    output_path: Path,
    evaluation_name: str,
    split: str = "test",
) -> Path:
    class_mapping = load_class_mapping(class_mapping_path)
    names = _dataset_class_names(dataset_yaml)
    if tuple(names) != TRAINING_CLASS_NAMES:
        raise PromotionError("Dataset class names do not match the versioned training taxonomy")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Install the ml dependency group to evaluate a model") from exc

    metrics = YOLO(str(weights_path)).val(data=str(dataset_yaml), split=split, plots=True)
    class_recalls = _per_class_recall(metrics, names)
    runtime_recall = _mapped_recall(class_recalls, class_mapping)
    results = getattr(metrics, "results_dict", {})
    evaluation = {
        "evaluation_name": evaluation_name,
        "weights_sha256": _sha256(weights_path),
        "dataset_yaml_sha256": _sha256(dataset_yaml),
        "overall": {
            "map50_95": float(results.get("metrics/mAP50-95(B)", metrics.box.map)),
            "map50": float(results.get("metrics/mAP50(B)", metrics.box.map50)),
            "precision": float(results.get("metrics/precision(B)", metrics.box.mp)),
            "recall": float(results.get("metrics/recall(B)", metrics.box.mr)),
        },
        "training_class_recall": class_recalls,
        "runtime_recall": runtime_recall,
    }
    _write_json(output_path, evaluation)
    return output_path


def package_candidate(
    weights_path: Path,
    dataset_manifest_path: Path,
    class_mapping_path: Path,
    evaluation_paths: list[Path],
    output_dir: Path,
    model_id: str,
    training_config_path: Path,
) -> Path:
    class_mapping = load_class_mapping(class_mapping_path)
    if not dataset_manifest_path.is_file():
        raise PromotionError(f"Dataset manifest is missing: {dataset_manifest_path}")
    evaluations = [_load_json(path) for path in evaluation_paths]
    if {value["evaluation_name"] for value in evaluations} != {"v4_test", "barn_holdout"}:
        raise PromotionError("Candidate requires v4_test and barn_holdout evaluations")
    for evaluation in evaluations:
        if evaluation["weights_sha256"] != _sha256(weights_path):
            raise PromotionError(f"Evaluation does not belong to candidate weights: {evaluation['evaluation_name']}")

    candidate_dir = output_dir / model_id
    candidate_dir.mkdir(parents=True, exist_ok=False)
    model_file = candidate_dir / "chicken_threat_detector.pt"
    shutil.copy2(weights_path, model_file)
    shutil.copy2(dataset_manifest_path, candidate_dir / "dataset_manifest.json")
    shutil.copy2(class_mapping_path, candidate_dir / "class_mapping.yaml")
    shutil.copy2(training_config_path, candidate_dir / "training_config.yaml")
    for path in evaluation_paths:
        shutil.copy2(path, candidate_dir / f"{_load_json(path)['evaluation_name']}.json")

    manifest = {
        "model_id": model_id,
        "model_file": model_file.name,
        "model_sha256": _sha256(model_file),
        "dataset_manifest_sha256": _sha256(dataset_manifest_path),
        "class_names": list(TRAINING_CLASS_NAMES),
        "runtime_class_names": list(RUNTIME_CLASS_NAMES),
        "class_mapping": class_mapping,
        "training_config_sha256": _sha256(training_config_path),
        "git_commit": _git_commit(),
        "environment": {"python": sys.version.split()[0]},
        "evaluations": {value["evaluation_name"]: value for value in evaluations},
        "review": {"false_alarm_samples_reviewed": False},
    }
    _write_yaml(candidate_dir / "candidate_manifest.yaml", manifest)
    return candidate_dir


def compare_candidate(candidate_manifest_path: Path, baseline_manifest_path: Path, policy_path: Path) -> list[str]:
    candidate = _load_yaml(candidate_manifest_path)
    baseline = _load_yaml(baseline_manifest_path)
    policy = _load_yaml(policy_path)
    failures: list[str] = []
    max_map_drop = float(policy["max_map50_95_drop"])
    max_recall_drop = float(policy["max_runtime_recall_drop"])
    for evaluation_name in ("v4_test", "barn_holdout"):
        candidate_evaluation = candidate["evaluations"].get(evaluation_name)
        baseline_evaluation = baseline["evaluations"].get(evaluation_name)
        if candidate_evaluation is None or baseline_evaluation is None:
            failures.append(f"Missing {evaluation_name} evaluation")
            continue
        candidate_map = float(candidate_evaluation["overall"]["map50_95"])
        baseline_map = float(baseline_evaluation["overall"]["map50_95"])
        if candidate_map + max_map_drop < baseline_map:
            failures.append(
                f"{evaluation_name} mAP50-95 regressed from {baseline_map:.4f} to {candidate_map:.4f}"
            )
        for label in policy["required_runtime_labels"]:
            candidate_recall = float(candidate_evaluation["runtime_recall"].get(label, 0.0))
            baseline_recall = float(baseline_evaluation["runtime_recall"].get(label, 0.0))
            if candidate_recall + max_recall_drop < baseline_recall:
                failures.append(
                    f"{evaluation_name} {label} recall regressed from "
                    f"{baseline_recall:.4f} to {candidate_recall:.4f}"
                )
    return failures


def promote_model(
    candidate_manifest_path: Path,
    baseline_manifest_path: Path,
    policy_path: Path,
    production_model_dir: Path,
    approve: bool,
) -> Path:
    if not approve:
        raise PromotionError("Manual approval is required; pass --approve after reviewing the reports")
    failures = compare_candidate(candidate_manifest_path, baseline_manifest_path, policy_path)
    if failures:
        raise PromotionError("Promotion gate failed:\n" + "\n".join(failures))
    candidate = _load_yaml(candidate_manifest_path)
    if not candidate["review"].get("false_alarm_samples_reviewed"):
        raise PromotionError("Candidate manifest must record false_alarm_samples_reviewed: true")
    candidate_dir = candidate_manifest_path.parent
    source_model = candidate_dir / candidate["model_file"]
    if _sha256(source_model) != candidate["model_sha256"]:
        raise PromotionError("Candidate model checksum does not match its manifest")
    production_model_dir.mkdir(parents=True, exist_ok=True)
    target_model = production_model_dir / "chicken_threat_detector.pt"
    shutil.copy2(source_model, target_model)
    manifest = {
        "model_id": candidate["model_id"],
        "file": target_model.name,
        "sha256": _sha256(target_model),
        "training_classes": candidate["class_names"],
        "runtime_classes": candidate["runtime_class_names"],
        "class_mapping": candidate["class_mapping"],
        "dataset_manifest_sha256": candidate["dataset_manifest_sha256"],
        "git_commit": candidate["git_commit"],
        "training_config_sha256": candidate["training_config_sha256"],
        "evaluations": candidate["evaluations"],
        "thresholds": {"confidence": 0.35, "image_size": 640},
    }
    _write_yaml(production_model_dir / "model_manifest.yaml", manifest)
    return production_model_dir / "model_manifest.yaml"


def _dataset_class_names(dataset_yaml: Path) -> list[str]:
    values = _load_yaml(dataset_yaml)
    names = values.get("names")
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names, key=int)]
    return [str(name) for name in names]


def _per_class_recall(metrics, names: list[str]) -> dict[str, float]:
    indices = list(getattr(metrics.box, "ap_class_index", range(len(names))))
    recalls = list(getattr(metrics.box, "r", []))
    return {names[int(index)]: float(recalls[position]) for position, index in enumerate(indices)}


def _mapped_recall(class_recalls: dict[str, float], mapping: dict[str, str]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {label: [] for label in RUNTIME_CLASS_NAMES}
    for training_label, runtime_label in mapping.items():
        if training_label in class_recalls:
            grouped[runtime_label].append(class_recalls[training_label])
    return {
        runtime_label: sum(values) / len(values) if values else 0.0
        for runtime_label, values in grouped.items()
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("GITHUB_SHA", "unknown")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, object]:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(values, dict):
        raise PromotionError(f"{path} must contain a mapping")
    return values


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
