# Chicken-Threat ML Workflow

The repository contains the code and configuration for the dataset and model lifecycle; source images, generated datasets, candidate weights, and evaluation data remain outside Git.

Each source metadata CSV must provide `image_path`, `label_path`, `source`, `capture_group`, `lighting`, and `split`; `captured_at` is optional. `capture_group` may appear in only one split.

Use `smart-home-ml-build-dataset` in Colab to create the dataset archive and inspection bundle. Upload an approved archive manually to Kaggle. Train and evaluate a candidate in Kaggle, including both `v4_test` and `barn_holdout`, then package it locally. Promotion requires a clean comparison to the current production baseline, explicit false-alarm review in the candidate manifest, and `--approve`.

The only model admitted to a SmartHomeBridge release is `src/smart_home_inference/models/chicken_thread/model/chicken_threat_detector.pt`, tracked by Git LFS and verified against `model_manifest.yaml`.
