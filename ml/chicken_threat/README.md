# Chicken-Threat ML Workflow

The repository contains the code and configuration for the dataset and model lifecycle; source images, generated datasets, candidate weights, and evaluation data remain outside Git.

Each source metadata CSV must provide `image_path`, `label_path`, `source`, `capture_group`, `lighting`, and `split`; `captured_at` is optional. `capture_group` may appear in only one split.

Prepare datasets locally in the ignored `ml/chicken_threat/work/` workspace. To acquire the configured Roboflow, Open Images, and supported LILA sources, set `ROBOFLOW_API_KEY` in the process environment and run:

```powershell
$env:ROBOFLOW_API_KEY = "..."
uv run --extra ml smart-home-ml-download-datasets
```

The downloader reports each source's start, cache/refresh decision, provider phase, per-split or per-candidate progress, record count, duration, and any failure immediately. It stores source images and YOLO labels below `work/raw/`, remote metadata below `work/cache/`, source provenance below `work/manifests/`, and writes `work/source_metadata.csv` plus `work/download_report.json`. Re-run it to resume complete sources; use repeatable `--source NAME`, `--refresh NAME`, or `--refresh-all` to control acquisition. Add `--verbose` to print a full traceback as soon as a source fails. The UNSW Predators entry is reported as skipped because its public metadata does not contain usable object boxes.

Inspect `download_report.json`, then build the validated training archive explicitly:

```bash
uv run --extra ml smart-home-ml-prepare-local-dataset
```

The command writes the built dataset, inspection report, inspection bundle, and dataset archive below `ml/chicken_threat/work/datasets/`. This avoids transferring raw source data to and from Colab. Inspect the report and bundle locally, then upload only an approved archive to Kaggle for candidate training. Train and evaluate a candidate in Kaggle, including both `v4_test` and `barn_holdout`, then package it locally. Promotion requires a clean comparison to the current production baseline, explicit false-alarm review in the candidate manifest, and `--approve`.

The only model admitted to a SmartHomeBridge release is `src/smart_home_inference/models/chicken_thread/model/chicken_threat_detector.pt`, tracked by Git LFS and verified against `model_manifest.yaml`.
