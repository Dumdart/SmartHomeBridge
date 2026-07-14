from pathlib import Path

from smart_home_inference.models.chicken_thread.model_manifest import (
    EXPECTED_CLASS_MAPPING,
    EXPECTED_RUNTIME_CLASSES,
    EXPECTED_TRAINING_CLASSES,
    default_model_path,
    load_production_model_manifest,
    verify_production_model,
)


def test_production_model_manifest_matches_the_runtime_taxonomy_and_checksum():
    manifest = load_production_model_manifest()

    assert manifest.training_classes == EXPECTED_TRAINING_CLASSES
    assert manifest.runtime_classes == EXPECTED_RUNTIME_CLASSES
    assert manifest.class_mapping == EXPECTED_CLASS_MAPPING
    assert verify_production_model(default_model_path()) == manifest


def test_only_the_approved_model_is_lfs_managed_in_the_current_tree():
    attributes = Path(".gitattributes").read_text()
    model_dir = Path("src/smart_home_inference/models/chicken_thread/model")

    assert "chicken_threat_detector.pt filter=lfs" in attributes
    assert (model_dir / "chicken_threat_detector.pt").is_file()
    assert not (model_dir / "chicken_threat_detector_best_v1.pt").exists()
    assert not (model_dir / "chicken_threat_detector_best_v3.pt").exists()
