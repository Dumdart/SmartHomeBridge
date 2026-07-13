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
