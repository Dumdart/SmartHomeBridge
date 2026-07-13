import csv
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from smart_home_ml.chicken_threat.artifacts import compare_candidate
from smart_home_ml.chicken_threat import cli
from smart_home_ml.chicken_threat import downloads
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


def test_download_command_uses_default_workspace_and_forwards_controls(monkeypatch, capsys):
    captured = {}

    def fake_download(workspace, config_path, source_names, refresh_sources, refresh_all, verbose):
        captured.update(
            workspace=workspace,
            config_path=config_path,
            source_names=source_names,
            refresh_sources=refresh_sources,
            refresh_all=refresh_all,
            verbose=verbose,
        )
        return Path("metadata.csv")

    monkeypatch.setattr(cli, "download_datasets", fake_download)
    monkeypatch.setattr(
        "sys.argv",
        [
            "smart-home-ml-download-datasets",
            "--source",
            "open_images",
            "--refresh",
            "open_images",
        ],
    )

    cli.download_datasets_main()

    assert captured == {
        "workspace": Path("ml/chicken_threat/work"),
        "config_path": None,
        "source_names": ["open_images"],
        "refresh_sources": ["open_images"],
        "refresh_all": False,
        "verbose": False,
    }
    assert capsys.readouterr().out.strip() == "metadata.csv"


def test_download_requires_roboflow_key_before_creating_workspace(tmp_path, monkeypatch):
    config_path = _write_download_config(
        tmp_path,
        {"poultry": {"type": "roboflow_yolo", "enabled": True}},
    )
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)

    with pytest.raises(downloads.DatasetDownloadError, match="ROBOFLOW_API_KEY"):
        downloads.download_datasets(tmp_path / "work", config_path)

    assert not (tmp_path / "work").exists()


def test_download_filters_refreshes_and_resumes_records(tmp_path, monkeypatch):
    config_path = _write_download_config(
        tmp_path,
        {
            "first": {"type": "fixture", "enabled": True},
            "second": {"type": "fixture", "enabled": True},
        },
    )
    calls = []

    def fake_download_source(name, source, workspace, seed, refresh):
        calls.append((name, refresh))
        records = []
        for index, split in enumerate(("train", "valid", "test")):
            image = workspace / "raw" / name / split / "images" / f"image-{index}.jpg"
            label = workspace / "raw" / name / split / "labels" / f"image-{index}.txt"
            image.parent.mkdir(parents=True, exist_ok=True)
            label.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (12, 12), (20 + index * 80, 20, 20)).save(image)
            label.write_text("0 0.5 0.5 0.2 0.2\n")
            records.append(downloads.DownloadRecord(image, label, name, f"{name}:{split}", "day", split))
        return records, {"name": name, "status": "downloaded", "records": len(records)}

    monkeypatch.setattr(downloads, "_download_source", fake_download_source)
    metadata_path = downloads.download_datasets(
        tmp_path / "work",
        config_path,
        source_names=["second"],
        refresh_sources=["second"],
    )

    assert calls == [("second", True)]
    rows = list(csv.DictReader(metadata_path.open()))
    assert {row["source"] for row in rows} == {"second"}
    built_dataset = build_dataset(
        metadata_path,
        tmp_path / "work" / "datasets",
        Path("ml/chicken_threat/configs/class_mapping.yaml"),
        "v5.0.0",
        dataset_config_path=Path("ml/chicken_threat/configs/dataset.yaml"),
    )
    assert (built_dataset / "data.yaml").is_file()
    report = json.loads((tmp_path / "work" / "download_report.json").read_text())
    assert report["selected_sources"] == ["second"]
    assert report["refresh_sources"] == ["second"]


def test_download_writes_actionable_failure_report(tmp_path, monkeypatch, capsys):
    config_path = _write_download_config(tmp_path, {"broken": {"type": "fixture", "enabled": True}})

    def fake_download_source(*_args, **_kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(downloads, "_download_source", fake_download_source)

    with pytest.raises(downloads.DatasetDownloadError, match="network unavailable"):
        downloads.download_datasets(tmp_path / "work", config_path)

    report = json.loads((tmp_path / "work" / "download_report.json").read_text())
    assert report["errors"] == ["broken: network unavailable"]
    output = capsys.readouterr().out
    assert "[1/1] broken (fixture): starting" in output
    assert "[1/1] broken: FAILED" in output


def test_source_adapter_reuses_complete_manifest(tmp_path):
    workspace = tmp_path / "work"
    image = workspace / "raw" / "fixture" / "train" / "images" / "image.jpg"
    label = workspace / "raw" / "fixture" / "train" / "labels" / "image.txt"
    image.parent.mkdir(parents=True)
    label.parent.mkdir(parents=True)
    Image.new("RGB", (12, 12), (20, 20, 20)).save(image)
    label.write_text("0 0.5 0.5 0.2 0.2\n")
    manifest_path = workspace / "manifests" / "fixture.json"
    manifest_path.parent.mkdir(parents=True)
    record = downloads.DownloadRecord(image, label, "fixture", "fixture:one", "day", "train")
    downloads._write_manifest(manifest_path, workspace, [record], {"name": "fixture", "status": "downloaded"})

    records, report = downloads._download_source(
        "fixture", {"type": "not_a_real_provider"}, workspace, 42, refresh=False
    )

    assert records == [record]
    assert report == {"name": "fixture", "status": "cached", "records": 1}


def test_yolo_adapter_converts_polygons_and_preserves_source_split(tmp_path):
    source_root = tmp_path / "source"
    image_path = source_root / "valid" / "images" / "sample.jpg"
    label_path = source_root / "valid" / "labels" / "sample.txt"
    image_path.parent.mkdir(parents=True)
    label_path.parent.mkdir(parents=True)
    Image.new("RGB", (12, 12), (20, 20, 20)).save(image_path)
    label_path.write_text("0 0.1 0.1 0.7 0.1 0.7 0.7 0.1 0.7\n")
    (source_root / "data.yaml").write_text("names: [Fox]\n")

    records = downloads._copy_yolo_source(
        source_root,
        tmp_path / "work" / "raw" / "fixture",
        "fixture",
        {"Fox": "fox"},
        keep_empty_images=False,
    )

    assert len(records) == 1
    assert records[0].split == "valid"
    assert records[0].label_path.read_text().strip() == "3 0.400000 0.400000 0.600000 0.600000"


def test_lila_adapter_writes_boxes_and_keeps_capture_groups_in_one_split(tmp_path, monkeypatch):
    metadata = {
        "categories": [{"id": 1, "name": "fox"}],
        "images": [
            {"id": 1, "file_name": "camera/2026-07-10_21-30.jpg", "location": "camera-a"}
        ],
        "annotations": [{"image_id": 1, "category_id": 1, "bbox": [1, 2, 5, 4]}],
    }

    def fake_download(url, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith("metadata.json"):
            destination.write_text(json.dumps(metadata))
        else:
            Image.new("RGB", (10, 10), (20, 20, 20)).save(destination)
        return destination

    monkeypatch.setattr(downloads, "_download_file", fake_download)
    source = {
        "metadata_url": "https://example.test/metadata.json",
        "image_base_url": "https://example.test/images",
        "class_map": {"fox": "fox"},
        "object_caps": {split: {"fox": 2} for split in ("train", "valid", "test")},
    }

    records, report = downloads._download_lila_coco(
        "lila_fixture", source, tmp_path / "work", tmp_path / "work" / "raw" / "lila_fixture", 42
    )

    assert report["skipped_downloads"] == 0
    assert len(records) == 1
    assert records[0].capture_group == "lila_fixture:camera-a"
    assert records[0].lighting == "night"
    assert records[0].label_path.read_text().strip() == "3 0.350000 0.400000 0.500000 0.400000"
    assert records[0].split == downloads._stable_split(records[0].capture_group)


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


def _write_download_config(tmp_path, sources):
    path = tmp_path / "download_sources.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "seed": 42,
                "canonical_classes": list(downloads.TRAINING_CLASS_NAMES),
                "sources": sources,
            }
        )
    )
    return path
