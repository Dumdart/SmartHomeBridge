import asyncio
import json
from types import SimpleNamespace

from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatInferenceService,
    DangerScorer,
    LocalChickenThreadDetector,
    chicken_thread_detector,
    chicken_thread_detector_controller,
    chicken_thread_detector_mqtt_callbacks,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_message import (
    handle_chicken_thread_detector_mqtt_message,
)
from smart_home_bridge.config import (
    CameraConfig,
    ChickenThreatConfig,
    DoorApiConfig,
    HttpConfig,
    MqttConfig,
    app_config,
)
from smart_home_bridge.models import Detection, DetectionFrame, ThreatLevel


def test_danger_scorer_maps_wild_mammal_alias_to_critical_threat():
    scorer = DangerScorer()

    assessment = scorer.score([Detection(label="fox", confidence=0.96)])

    assert assessment.level == ThreatLevel.CRITICAL
    assert assessment.score == 0.912
    assert assessment.triggering_detections[0].label == "fox"


def test_detector_controller_scores_frame_and_publishes_assessment():
    published_payloads = []
    detector = chicken_thread_detector(2, "thread-detector")

    async def publishable(payload):
        published_payloads.append(payload)

    controller = chicken_thread_detector_controller(detector, publishable=publishable)
    payload = {
        "source": "coop-camera",
        "detections": [
            {"label": "chicken", "confidence": 0.99},
            {"label": "dog", "confidence": 0.9},
        ],
    }

    result = asyncio.run(controller.score_frame_from_json(json.dumps(payload)))

    assert result.success is True
    assert detector.assessment.level == ThreatLevel.MEDIUM
    assert json.loads(published_payloads[0])["level"] == "medium"


def test_mqtt_callback_decodes_detection_payload_and_scores_state():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    callbacks = chicken_thread_detector_mqtt_callbacks(controller)
    payload = json.dumps(
        {
            "detections": [
                {"label": "bird_of_prey", "confidence": 0.8},
            ]
        }
    )
    message = SimpleNamespace(topic="loxone/chicken-thread-detector", payload=payload.encode())

    callbacks.on_message(None, None, message)

    assert detector.assessment.level == ThreatLevel.MEDIUM


def test_detector_message_decodes_detection_payload_and_scores_state():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    payload = json.dumps(
        {
            "detections": [
                {"label": "bird_of_prey", "confidence": 0.8},
            ]
        }
    )

    asyncio.run(
        handle_chicken_thread_detector_mqtt_message(
            "loxone/chicken-thread-detector",
            payload.encode(),
            controller,
        )
    )

    assert detector.assessment.level == ThreatLevel.MEDIUM


def test_detector_message_ignores_published_assessment_payloads():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    payload = json.dumps({"level": "high", "score": 0.75})

    asyncio.run(
        handle_chicken_thread_detector_mqtt_message(
            "loxone/chicken-thread-detector",
            payload.encode(),
            controller,
        )
    )

    assert detector.assessment.level == ThreatLevel.NONE


def test_mqtt_callback_ignores_published_assessment_payloads():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    callbacks = chicken_thread_detector_mqtt_callbacks(controller)
    payload = json.dumps({"level": "high", "score": 0.75})
    message = SimpleNamespace(topic="loxone/chicken-thread-detector", payload=payload.encode())

    callbacks.on_message(None, None, message)

    assert detector.assessment.level == ThreatLevel.NONE


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

    class FakeModel:
        def predict(self, image, conf, imgsz, verbose):
            assert image == "decoded-image"
            assert conf == 0.35
            assert imgsz == 640
            assert verbose is False
            return [FakeResult()]

    detector = LocalChickenThreadDetector(model=FakeModel())

    frame = detector.detect("decoded-image", source="esp32cam")

    assert frame.source == "esp32cam"
    assert frame.detections[0].label == "wild_mammal_threat"
    assert frame.detections[0].confidence == 0.96
    assert frame.detections[0].box.left == 0.1


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


def test_application_wires_thread_detector_to_mqtt_publish():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
        ),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="loxone",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
    )
    published = []

    class FakeMqttClient:
        async def publish(self, topic, payload, on_publish=None):
            published.append((topic, json.loads(payload)))

    app = App(config, mqtt_client_factory=lambda _: FakeMqttClient())

    result = asyncio.run(
        app.thread_detector_controller.score_frame_from_json(
            json.dumps({"detections": [{"label": "wild_mammal_threat", "confidence": 0.95}]})
        )
    )

    assert result.success is True
    assert result.data.level == ThreatLevel.CRITICAL
    assert published == [
        (
            "loxone/chicken-thread-detector",
            {
                "level": "critical",
                "score": 0.9025,
                "detection_count": 1,
                "triggering_detections": [
                    {
                        "label": "wild_mammal_threat",
                        "confidence": 0.95,
                        "box": None,
                    }
                ],
            },
        )
    ]


def test_application_does_not_build_threat_pipeline_when_disabled():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
        ),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="loxone",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        chicken_threat=ChickenThreatConfig(enabled=False),
    )

    app = App(config)

    assert app.chicken_threat_pipeline is None


def test_application_wires_independent_camera_threat_pipeline():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
        ),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="loxone",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        camera=CameraConfig(host="esp32cam.local", port=80),
        chicken_threat=ChickenThreatConfig(
            enabled=True,
            model_path="/models/chicken_threat_detector_best.pt",
            poll_interval_seconds=7,
        ),
    )

    app = App(config)

    assert app.chicken_threat_pipeline is not None
    assert app.chicken_threat_pipeline.camera_client.config == config.camera
    assert app.chicken_threat_pipeline.poll_interval_seconds == 7
    assert app.thread_model_config.model_path == "/models/chicken_threat_detector_best.pt"
    assert app.http_gate is app.composition.http_gate


def test_threat_pipeline_run_publishes_assessment():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            base_url="http://door.local",
            username="user",
            password="password",
        ),
        mqtt=MqttConfig(
            host="mqtt.local",
            port=8883,
            username="user",
            password="password",
            base_topic="loxone",
        ),
        http=HttpConfig(host="localhost", port=8080),
        log_level="INFO",
        camera=CameraConfig(host="esp32cam.local", port=80),
        chicken_threat=ChickenThreatConfig(enabled=True),
    )
    published = []

    class FakeCameraClient:
        def fetch_jpeg(self):
            return b"\xff\xd8frame"

        def health(self):
            return True

    class FakeInferenceService:
        def detect(self, image_bytes, source=None):
            assert image_bytes == b"\xff\xd8frame"
            return DetectionFrame(
                detections=(Detection(label="dog", confidence=0.9),),
                source=source,
            )

    class FakeMqttClient:
        async def publish(self, topic, payload, on_publish=None):
            published.append((topic, json.loads(payload)))

    app = App(config, mqtt_client_factory=lambda _: FakeMqttClient())
    app.chicken_threat_pipeline.camera_client = FakeCameraClient()
    app.chicken_threat_pipeline.inference_service = FakeInferenceService()

    result = asyncio.run(app.chicken_threat_pipeline.run_once())

    assert result.success is True
    assert published == [
        (
            "loxone/chicken-thread-detector",
            {
                "level": "medium",
                "score": 0.675,
                "detection_count": 1,
                "triggering_detections": [
                    {
                        "label": "dog",
                        "confidence": 0.9,
                        "box": None,
                    }
                ],
            },
        )
    ]
