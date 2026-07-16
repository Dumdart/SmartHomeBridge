# Chicken-Threat ML Workflow

The repository contains the code and configuration for the dataset and model lifecycle; source images, generated datasets, candidate weights, and evaluation data remain outside Git.

Each source metadata CSV must provide `image_path`, `label_path`, `source`, `capture_group`, `lighting`, and `split`; `captured_at` is optional. `capture_group` may appear in only one split.

Prepare datasets locally in the ignored `ml/chicken_threat/work/` workspace. To acquire the configured Roboflow, Open Images, and supported LILA sources, set `ROBOFLOW_API_KEY` in the process environment and run:

```powershell
$env:ROBOFLOW_API_KEY = "..."
uv run --extra ml smart-home-ml-download-datasets
```

The downloader reports each source's start, cache/refresh decision, provider phase, selected-download progress, record count, duration, and any failure immediately. It stores source images and YOLO labels below `work/raw/`, remote metadata below `work/cache/`, source provenance below `work/manifests/`, and writes `work/source_metadata.csv` plus `work/download_report.json`. Re-run it to resume complete sources; use repeatable `--source NAME`, `--refresh NAME`, or `--refresh-all` to control acquisition. Add `--verbose` to print a full traceback as soon as a source fails. Open Images reuses split metadata between class shards, and LILA downloads selected candidates concurrently. The optional Chicken Barn Roboflow source produces a warning rather than discarding successful sources when no generated version exists. The UNSW Predators entry is reported as skipped because its public metadata does not contain usable object boxes.

To use a manually downloaded Roboflow YOLOv8 export instead of its API, pass the configured source name and zip path. The importer safely extracts the archive, remaps its source class IDs, writes the normalized raw data and manifest, and then removes the temporary extraction. A subset import retains records from all other complete source manifests when regenerating `source_metadata.csv`:

```powershell
uv run --extra ml smart-home-ml-download-datasets `
  --source chicken_barn_roboflow `
  --yolo-zip "chicken_barn_roboflow=C:\datasets\chicken-barn-yolov8.zip" `
  --verbose
```

Inspect `download_report.json`, then build the validated training archive explicitly:

```bash
uv run --extra ml smart-home-ml-prepare-local-dataset
```

Do not call downloader helpers such as `_write_source_metadata` from an ad-hoc Python snippet;
that helper writes only the records passed to it and can replace the combined CSV. The local
preparation command verifies that every completed manifest is represented before building. If
the check reports incomplete metadata, rerun the downloader for any cached source (for example
`--source poultry_roboflow`) to regenerate the combined CSV without reacquiring the datasets.

The command writes the built dataset, inspection report, inspection bundle, and dataset archive below `ml/chicken_threat/work/datasets/`. This avoids transferring raw source data to and from Colab. Inspect the report and bundle locally, then upload only an approved archive to Kaggle for candidate training.

Before training, the Kaggle notebook copies the attached dataset from read-only `/kaggle/input` to `/kaggle/working/chicken-threat-v5-dataset`. This is required because Ultralytics may normalize JPEG EXIF orientation while verifying images and writes cache files beside each split. Pointing training directly at `/kaggle/input` can make writable-image repairs fail and causes Ultralytics to report valid images as corrupt and ignore them. Wait for the copy cell to finish, confirm its `.copy-complete` marker exists, and then run training. If the copy cell is interrupted, rerun it; the incomplete destination is deleted and rebuilt automatically. Do not continue a run whose scan reports `ignoring corrupt image/label` with `Read-only file system`.

Train and evaluate a candidate in Kaggle, including both `v4_test` and `barn_holdout`, then package it locally. Promotion requires a clean comparison to the current production baseline, explicit false-alarm review in the candidate manifest, and `--approve`.

The only model admitted to a SmartHomeBridge release is `src/smart_home_inference/models/chicken_thread/model/chicken_threat_detector.pt`, tracked by Git LFS and verified against `model_manifest.yaml`.
