from __future__ import annotations

import argparse
import json
from pathlib import Path

from smart_home_ml.chicken_threat.artifacts import (
    compare_candidate,
    evaluate_model,
    package_candidate,
    promote_model,
    train_model,
)
from smart_home_ml.chicken_threat.dataset import build_dataset, inspect_dataset
from smart_home_ml.chicken_threat.downloads import (
    download_datasets,
    validate_metadata_manifest_coverage,
)


def build_dataset_main() -> None:
    parser = argparse.ArgumentParser(description="Build a validated chicken-threat YOLO dataset")
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--class-mapping", type=Path, required=True)
    parser.add_argument("--dataset-config", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sample-limit", type=int, default=24)
    args = parser.parse_args()
    print(build_dataset(args.metadata, args.output_dir, args.class_mapping, args.version, args.sample_limit, args.dataset_config))


def inspect_dataset_main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a built chicken-threat dataset")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_dataset(args.dataset, args.output_dir).to_dict(), indent=2))


def prepare_local_dataset_main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the chicken-threat dataset in the local ignored ML workspace"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("ml/chicken_threat/work"),
        help="Ignored workspace containing source_metadata.csv (default: %(default)s)",
    )
    parser.add_argument("--version", default="v5.0.0")
    parser.add_argument("--sample-limit", type=int, default=24)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    validate_metadata_manifest_coverage(workspace)
    repository_root = Path(__file__).resolve().parents[3]
    dataset_root = build_dataset(
        workspace / "source_metadata.csv",
        workspace / "datasets",
        repository_root / "ml/chicken_threat/configs/class_mapping.yaml",
        args.version,
        args.sample_limit,
        repository_root / "ml/chicken_threat/configs/dataset.yaml",
    )
    print(dataset_root)


def download_datasets_main() -> None:
    parser = argparse.ArgumentParser(
        description="Download chicken-threat source datasets into the local ignored ML workspace"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("ml/chicken_threat/work"),
        help="Ignored workspace for raw sources and generated source metadata (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Source configuration YAML (default: ml/chicken_threat/configs/download_sources.yaml)",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Source name to download; repeat to select multiple sources",
    )
    parser.add_argument(
        "--refresh",
        action="append",
        default=[],
        help="Selected source to acquire again instead of resuming cached output",
    )
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="Acquire all selected sources again instead of resuming cached output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full tracebacks for source failures as they occur",
    )
    parser.add_argument(
        "--yolo-zip",
        action="append",
        default=[],
        metavar="SOURCE=PATH",
        help="Use a local Roboflow YOLOv8 zip for a source instead of its API",
    )
    args = parser.parse_args()
    local_yolo_archives = {}
    for value in args.yolo_zip:
        source_name, separator, archive_path = value.partition("=")
        if not separator or not source_name or not archive_path:
            parser.error("--yolo-zip must use SOURCE=PATH")
        local_yolo_archives[source_name] = Path(archive_path)
    print(
        download_datasets(
            workspace=args.workspace,
            config_path=args.config,
            source_names=args.source,
            refresh_sources=args.refresh,
            refresh_all=args.refresh_all,
            verbose=args.verbose,
            local_yolo_archives=local_yolo_archives,
        )
    )


def train_main() -> None:
    parser = argparse.ArgumentParser(description="Train a chicken-threat candidate model")
    parser.add_argument("--dataset-yaml", type=Path, required=True)
    parser.add_argument("--training-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(train_model(args.dataset_yaml, args.training_config, args.output_dir))


def evaluate_main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a chicken-threat candidate model")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--dataset-yaml", type=Path, required=True)
    parser.add_argument("--class-mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluation-name", choices=("v4_test", "barn_holdout"), required=True)
    parser.add_argument("--split", default="test")
    args = parser.parse_args()
    print(evaluate_model(args.weights, args.dataset_yaml, args.class_mapping, args.output, args.evaluation_name, args.split))


def package_candidate_main() -> None:
    parser = argparse.ArgumentParser(description="Package a evaluated chicken-threat candidate")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--class-mapping", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--training-config", type=Path, required=True)
    args = parser.parse_args()
    print(package_candidate(args.weights, args.dataset_manifest, args.class_mapping, args.evaluation, args.output_dir, args.model_id, args.training_config))


def compare_baseline_main() -> None:
    parser = argparse.ArgumentParser(description="Compare a candidate with the approved baseline")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    failures = compare_candidate(args.candidate, args.baseline, args.policy)
    if failures:
        raise SystemExit("\n".join(failures))
    print("Promotion gate passed")


def promote_model_main() -> None:
    parser = argparse.ArgumentParser(description="Promote an approved chicken-threat candidate")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--production-model-dir", type=Path, required=True)
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()
    print(promote_model(args.candidate, args.baseline, args.policy, args.production_model_dir, args.approve))
