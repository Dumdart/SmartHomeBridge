# Chicken-Threat ML Workflow

The repository contains the code and configuration for the dataset and model lifecycle; source images, generated datasets, candidate weights, and evaluation data remain outside Git.

Each source metadata CSV must provide `image_path`, `label_path`, `source`, `capture_group`, `lighting`, and `split`; `captured_at` is optional. `capture_group` may appear in only one split.

Prepare datasets locally in the ignored `ml/chicken_threat/work/` workspace. Put the source images, YOLO labels, and a `source_metadata.csv` file in that directory (metadata paths may be relative to the CSV), then run:

```bash
uv run smart-home-ml-prepare-local-dataset
```

The command writes the built dataset, inspection report, inspection bundle, and dataset archive below `ml/chicken_threat/work/datasets/`. This avoids transferring raw source data to and from Colab. Inspect the report and bundle locally, then upload only an approved archive to Kaggle for candidate training. Train and evaluate a candidate in Kaggle, including both `v4_test` and `barn_holdout`, then package it locally. Promotion requires a clean comparison to the current production baseline, explicit false-alarm review in the candidate manifest, and `--approve`.

The only model admitted to a SmartHomeBridge release is `src/smart_home_inference/models/chicken_thread/model/chicken_threat_detector.pt`, tracked by Git LFS and verified against `model_manifest.yaml`.
