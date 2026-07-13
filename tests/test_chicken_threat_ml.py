import csv
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from smart_home_ml.chicken_threat.artifacts import compare_candidate
from smart_home_ml.chicken_threat import cli
from smart_home_ml.chicken_threat.dataset import (
    DatasetValidationError,
    build_dataset,
    load_source_metadata,
    validate_source_records,
)
from smart_home_ml.chicken_threat.taxonomy import load_class_mapping


def test_dataset_build_writes_manifest_inspection_bundle_and_archive(tmp_path):
    metadata_path = _write_source_dataset(tmp_path)
    output_dir = tmp_path / "output"
    dataset_root = build_dataset(
        metadata_path,
        output_dir,
            Path("ml/chicken_threat/configs/class_mapping.yaml"),
            "v5.0.0",
            sample_limit=2,
            dataset_config_path=Path("ml/chicken_threat/configs/dataset.yaml"),
    )

    manifest = json.loads((dataset_root / "dataset_manifest.json").read_text())

    assert manifest["class_names"][3] == "fox"
    assert (dataset_root / "inspection_report.html").is_file()
    assert (dataset_root / "inspection_bundle.zip").is_file()
    assert (output_dir / "v5.0.0.zip").is_file()


def test_dataset_validation_rejects_capture_group_leakage(tmp_path):
    metadata_path = _write_source_dataset(tmp_path, capture_groups=("sequence-1", "sequence-1", "sequence-3"))

    report = validate_source_records(load_source_metadata(metadata_path))

    assert not report.valid
    assert any("multiple splits" in error for error in report.errors)
    with pytest.raises(DatasetValidationError, match="multiple splits"):
        build_dataset(
            metadata_path,
            tmp_path / "output",
            Path("ml/chicken_threat/configs/class_mapping.yaml"),
            "v5.0.0",
            dataset_config_path=Path("ml/chicken_threat/configs/dataset.yaml"),
        )


def test_local_dataset_command_uses_the_ignored_workspace(monkeypatch, tmp_path, capsys):
    workspace = tmp_path / "work"
    built_dataset = workspace / "datasets" / "v5.0.0"
    captured = {}

    def fake_build_dataset(metadata, output_dir, class_mapping, version, sample_limit, dataset_config):
        captured.update(
            metadata=metadata,
            output_dir=output_dir,
            class_mapping=class_mapping,
            version=version,
            sample_limit=sample_limit,
            dataset_config=dataset_config,
        )
        return built_dataset

    monkeypatch.setattr(cli, "build_dataset", fake_build_dataset)
    monkeypatch.setattr(
        "sys.argv",
        ["smart-home-ml-prepare-local-dataset", "--workspace", str(workspace)],
    )

    cli.prepare_local_dataset_main()

    assert captured["metadata"] == workspace.resolve() / "source_metadata.csv"
    assert captured["output_dir"] == workspace.resolve() / "datasets"
    assert captured["version"] == "v5.0.0"
    assert captured["sample_limit"] == 24
    assert captured["class_mapping"].name == "class_mapping.yaml"
    assert captured["dataset_config"].name == "dataset.yaml"
    assert capsys.readouterr().out.strip() == str(built_dataset)


def test_dataset_validation_rejects_malformed_yolo_label(tmp_path):
    metadata_path = _write_source_dataset(tmp_path)
    (tmp_path / "label-0.txt").write_text("0 0.5 0.5 0.2\n")

    report = validate_source_records(load_source_metadata(metadata_path))

    assert not report.valid
    assert any("five YOLO values" in error for error in report.errors)


def test_class_mapping_requires_the_complete_nine_to_eight_contract(tmp_path):
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text("training_to_runtime:\n  fox: wild_mammal_threat\n")

    with pytest.raises(ValueError, match="exactly these training classes"):
        load_class_mapping(mapping_path)


def test_promotion_comparison_blocks_runtime_recall_regression(tmp_path):
    candidate_path = tmp_path / "candidate.yaml"
    baseline_path = tmp_path / "baseline.yaml"
    policy_path = tmp_path / "policy.yaml"
    baseline = _manifest(map50_95=0.6, recall=0.8)
    candidate = _manifest(map50_95=0.6, recall=0.7)
    baseline_path.write_text(yaml.safe_dump(baseline))
    candidate_path.write_text(yaml.safe_dump(candidate))
    policy_path.write_text(
        yaml.safe_dump(
            {
                "max_map50_95_drop": 0.0,
                "max_runtime_recall_drop": 0.0,
                "required_runtime_labels": ["wild_mammal_threat"],
            }
        )
    )

    failures = compare_candidate(candidate_path, baseline_path, policy_path)

    assert failures == [
        "v4_test wild_mammal_threat recall regressed from 0.8000 to 0.7000",
        "barn_holdout wild_mammal_threat recall regressed from 0.8000 to 0.7000",
    ]


def _write_source_dataset(tmp_path, capture_groups=("sequence-1", "sequence-2", "sequence-3")):
    rows = []
    for index, split in enumerate(("train", "valid", "test")):
        image_path = tmp_path / f"image-{index}.jpg"
        label_path = tmp_path / f"label-{index}.txt"
        Image.new("RGB", (16, 16), (index * 10, 10, 10)).save(image_path, format="JPEG")
        label_path.write_text("0 0.5 0.5 0.2 0.2\n")
        rows.append(
            {
                "image_path": image_path.name,
                "label_path": label_path.name,
                "source": "barn-camera",
                "capture_group": capture_groups[index],
                "lighting": "day" if index != 2 else "night",
                "split": split,
                "captured_at": "2026-07-10T12:00:00Z",
            }
        )
    metadata_path = tmp_path / "metadata.csv"
    with metadata_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return metadata_path


def _manifest(map50_95, recall):
    evaluation = {
        "overall": {"map50_95": map50_95},
        "runtime_recall": {"wild_mammal_threat": recall},
    }
    return {"evaluations": {"v4_test": evaluation, "barn_holdout": evaluation}}
