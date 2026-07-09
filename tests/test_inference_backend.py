import ast
import builtins
import tomllib
from pathlib import Path

from starlette.testclient import TestClient

from smart_home_contracts.chicken_thread import BoundingBox, Detection, DetectionFrame
from smart_home_inference.api import create_app
from smart_home_inference.exceptions import ImageTooLargeError, InvalidImageError
from smart_home_inference.models.chicken_thread import (
    ChickenThreatInferenceService,
    LocalChickenThreadDetector,
    _decode_jpeg,
)
from smart_home_inference.registry import ModelRegistry


class FakeModel:
    identifier = "chicken-threat"

    def __init__(self, frame=None, ready=True, detail=None):
        self.frame = frame or DetectionFrame()
        self.ready_value = ready
        self.detail = detail
        self.ready_calls = 0
        self.infer_calls = []

    def ready(self):
        self.ready_calls += 1
        return self.ready_value, self.detail

    def infer(self, image_bytes, source=None):
        self.infer_calls.append((image_bytes, source))
        return self.frame


def test_health_endpoint_succeeds_without_loading_model():
    model = FakeModel()
    client = TestClient(create_app(ModelRegistry([model])))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert model.ready_calls == 0


def test_ready_endpoint_reports_model_load_failure_clearly():
    model = FakeModel(ready=False, detail="model file missing")
    client = TestClient(create_app(ModelRegistry([model])))

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "ready": False,
        "models": {
            "chicken-threat": {
                "ready": False,
                "detail": "model file missing",
            }
        },
    }


def test_models_endpoint_lists_chicken_threat():
    client = TestClient(create_app(ModelRegistry([FakeModel()])))

    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json() == {"models": ["chicken-threat"]}


def test_chicken_threat_endpoint_rejects_non_jpeg_content_type():
    client = TestClient(create_app(ModelRegistry([FakeModel()])))

    response = client.post(
        "/v1/chicken-threat/infer",
        content=b"not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_content_type"


def test_chicken_threat_endpoint_rejects_invalid_image_bytes():
    def reject_invalid(_image_bytes):
        raise InvalidImageError("Image payload is not a valid JPEG image.")

    service = ChickenThreatInferenceService(
        detector=FakeDetector(),
        image_decoder=reject_invalid,
    )
    client = TestClient(create_app(ModelRegistry([service])))

    response = client.post(
        "/v1/chicken-threat/infer",
        content=b"not-jpeg",
        headers={"content-type": "image/jpeg"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_image"


def test_chicken_threat_endpoint_rejects_oversized_images():
    def reject_oversized(_image_bytes):
        raise ImageTooLargeError("Image exceeds 4000000 pixels: 3000x3000")

    service = ChickenThreatInferenceService(
        detector=FakeDetector(),
        image_decoder=reject_oversized,
    )
    client = TestClient(create_app(ModelRegistry([service])))

    response = client.post(
        "/v1/chicken-threat/infer",
        content=b"jpeg",
        headers={"content-type": "image/jpeg"},
    )

    assert response.status_code == 413
    assert response.json()["error"] == "image_too_large"


def test_chicken_threat_endpoint_returns_raw_detections_for_fake_model():
    frame = DetectionFrame(
        detections=(
            Detection(
                label="wild_mammal_threat",
                confidence=0.96,
                box=BoundingBox(left=0.1, top=0.2, right=0.3, bottom=0.4),
            ),
        ),
        source=None,
    )
    model = FakeModel(frame=frame)
    client = TestClient(create_app(ModelRegistry([model])))

    response = client.post(
        "/v1/models/chicken-threat/infer",
        content=b"jpeg-bytes",
        headers={"content-type": "image/jpeg"},
    )

    assert response.status_code == 200
    assert response.json() == frame.to_dict()
    assert model.infer_calls == [(b"jpeg-bytes", None)]


def test_model_registry_resolves_known_models_and_rejects_unknown_models():
    model = FakeModel()
    registry = ModelRegistry([model])

    assert registry.get("chicken-threat") is model

    try:
        registry.get("unknown")
    except Exception as exc:
        assert str(exc) == "Unknown model: unknown"
    else:
        raise AssertionError("Expected unknown model to be rejected")


def test_local_detector_maps_fake_model_result_to_detection_frame():
    class FakeValue:
        def __init__(self, value):
            self.value = value

        def item(self):
            return self.value

    class FakeCoordinates:
        def __getitem__(self, index):
            assert index == 0
            return self

        def tolist(self):
            return [0.1, 0.2, 0.3, 0.4]

    class FakeBox:
        cls = FakeValue(5)
        conf = FakeValue(0.96)
        xyxyn = FakeCoordinates()

    class FakeResult:
        names = {5: "fox"}
        boxes = [FakeBox()]

    class FakeYoloModel:
        def predict(self, image, conf, imgsz, verbose):
            assert image == "decoded-image"
            assert conf == 0.35
            assert imgsz == 640
            assert verbose is False
            return [FakeResult()]

    detector = LocalChickenThreadDetector(model=FakeYoloModel())

    frame = detector.detect("decoded-image", source="esp32cam")

    assert frame.source == "esp32cam"
    assert frame.detections[0].label == "wild_mammal_threat"
    assert frame.detections[0].confidence == 0.96
    assert frame.detections[0].box.left == 0.1


def test_local_detector_import_error_reports_underlying_native_library(monkeypatch):
    real_import = builtins.__import__

    def import_with_missing_native_library(name, *args, **kwargs):
        if name == "ultralytics":
            raise ImportError("libxcb.so.1: cannot open shared object file")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_with_missing_native_library)
    detector = LocalChickenThreadDetector()

    try:
        detector._model()
    except RuntimeError as exc:
        message = str(exc)
        assert "Unable to import ultralytics" in message
        assert "libxcb.so.1" in message
        assert "native OpenCV libraries" in message
    else:
        raise AssertionError("Expected ultralytics import failure")


def test_inference_service_decodes_jpeg_bytes_before_detection():
    class FakeDetector:
        def __init__(self):
            self.calls = []

        def detect(self, image, source=None):
            self.calls.append((image, source))
            return {"frame": source}

    fake_detector = FakeDetector()
    service = ChickenThreatInferenceService(
        detector=fake_detector,
        image_decoder=lambda image_bytes: f"decoded:{image_bytes.decode()}",
    )

    frame = service.detect(b"jpeg-bytes", source="esp32cam")

    assert frame == {"frame": "esp32cam"}
    assert fake_detector.calls == [("decoded:jpeg-bytes", "esp32cam")]


def test_inference_decoder_rejects_oversized_image(monkeypatch):
    from smart_home_inference.models.chicken_thread import inference

    def reject_image(_image):
        raise RuntimeError("Image exceeds 4000000 pixels: test")

    monkeypatch.setattr(inference, "validate_image_size", reject_image)

    try:
        _decode_jpeg(_jpeg_bytes())
    except RuntimeError as exc:
        assert "exceeds 4000000 pixels" in str(exc)
    else:
        raise AssertionError("Expected oversized inference image to be rejected")


def test_inference_backend_does_not_import_bridge_runtime_modules():
    inference_root = Path("src/smart_home_inference")

    for path in inference_root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported_names = [node.module or ""]
            else:
                continue

            assert all(
                not name.startswith("smart_home_bridge") for name in imported_names
            ), f"{path} imports a bridge runtime module"


def test_bridge_runtime_dependencies_do_not_include_inference_only_packages():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    runtime_dependencies = set(pyproject["project"]["dependencies"])
    inference_dependencies = set(pyproject["project"]["optional-dependencies"]["inference"])

    assert "Pillow" not in runtime_dependencies
    assert "ultralytics" not in runtime_dependencies
    assert "Pillow" in inference_dependencies
    assert "ultralytics" in inference_dependencies


def test_bridge_runtime_modules_do_not_import_inference_backend_modules():
    bridge_root = Path("src/smart_home_bridge")

    for path in bridge_root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported_names = [node.module or ""]
            else:
                continue

            assert all(
                not name.startswith("smart_home_inference") for name in imported_names
            ), f"{path} imports an inference backend module"


class FakeDetector:
    def ready(self):
        return True, None

    def detect(self, image, source=None):
        return DetectionFrame(source=source)


def _jpeg_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (10, 10), "white").save(output, format="JPEG")
    return output.getvalue()
