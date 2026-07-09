import asyncio
import json
from types import SimpleNamespace

import pytest

from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatInferenceClient,
    DangerScorer,
    chicken_thread_detector,
    chicken_thread_detector_controller,
    chicken_thread_detector_mqtt_callbacks,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_message import (
    MAX_DETECTIONS_PER_MESSAGE,
    MAX_DETECTOR_PAYLOAD_BYTES,
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
from smart_home_contracts.chicken_thread import DetectionFrame, Detection, ThreatLevel


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


def test_detector_message_rejects_oversized_payload():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    payload = b"{" + (b" " * MAX_DETECTOR_PAYLOAD_BYTES)

    with pytest.raises(ValueError, match="Detector payload exceeds"):
        asyncio.run(
            handle_chicken_thread_detector_mqtt_message(
                "loxone/chicken-thread-detector",
                payload,
                controller,
            )
        )

    assert detector.assessment.level == ThreatLevel.NONE


def test_detector_message_rejects_too_many_detections():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    payload = json.dumps(
        {
            "detections": [
                {"label": "dog", "confidence": 0.9}
                for _ in range(MAX_DETECTIONS_PER_MESSAGE + 1)
            ]
        }
    )

    with pytest.raises(ValueError, match="more than"):
        asyncio.run(
            handle_chicken_thread_detector_mqtt_message(
                "loxone/chicken-thread-detector",
                payload.encode(),
                controller,
            )
        )

    assert detector.assessment.level == ThreatLevel.NONE


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


def test_mqtt_callback_ignores_retained_detection_payloads():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    callbacks = chicken_thread_detector_mqtt_callbacks(controller)
    payload = json.dumps({"detections": [{"label": "fox", "confidence": 0.96}]})
    message = SimpleNamespace(
        topic="loxone/chicken-thread-detector",
        payload=payload.encode(),
        retain=True,
    )

    callbacks.on_message(None, None, message)

    assert detector.assessment.level == ThreatLevel.NONE


def test_mqtt_callback_swallows_invalid_detection_payloads():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    callbacks = chicken_thread_detector_mqtt_callbacks(controller)
    payload = b"{" + (b" " * MAX_DETECTOR_PAYLOAD_BYTES)
    message = SimpleNamespace(
        topic="loxone/chicken-thread-detector",
        payload=payload,
        retain=False,
    )

    callbacks.on_message(None, None, message)

    assert detector.assessment.level == ThreatLevel.NONE


def test_http_inference_client_posts_jpeg_and_decodes_detection_frame(monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            return False

        def read(self):
            return json.dumps(
                {"detections": [{"label": "dog", "confidence": 0.9}], "source": None}
            ).encode()

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(
        "smart_home_bridge.bridge_devices.chicken_thread_detector.inference.urlopen",
        fake_urlopen,
    )
    client = ChickenThreatInferenceClient("http://inference.local/infer", 3)

    frame = client.detect(b"\xff\xd8frame", source="esp32cam")

    assert frame.source == "esp32cam"
    assert frame.detections[0].label == "dog"
    request, timeout = requests[0]
    assert request.full_url == "http://inference.local/infer"
    assert request.headers["Content-type"] == "image/jpeg"
    assert request.data == b"\xff\xd8frame"
    assert timeout == 3


def test_application_wires_thread_detector_to_mqtt_publish():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            api_key="api-key",
            device_id="device-id",
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
        async def publish(self, topic, payload, retain=False, on_publish=None):
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
            api_key="api-key",
            device_id="device-id",
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
            api_key="api-key",
            device_id="device-id",
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
            inference_url="http://inference.local:8090/v1/chicken-threat/infer",
            poll_interval_seconds=7,
        ),
    )

    app = App(config)

    assert app.chicken_threat_pipeline is not None
    assert app.chicken_threat_pipeline.camera_client.config == config.camera
    assert app.chicken_threat_pipeline.poll_interval_seconds == 7
    assert (
        app.threat_inference_service.inference_url
        == "http://inference.local:8090/v1/chicken-threat/infer"
    )
    assert app.http_gate is app.composition.http_gate


def test_threat_pipeline_run_publishes_assessment():
    from smart_home_bridge.__main__ import App

    config = app_config(
        door_api=DoorApiConfig(
            api_key="api-key",
            device_id="device-id",
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
        async def publish(self, topic, payload, retain=False, on_publish=None):
            published.append((topic, json.loads(payload)))

    app = App(config, mqtt_client_factory=lambda _: FakeMqttClient())
    app.chicken_threat_pipeline.camera_client = FakeCameraClient()
    app.chicken_threat_pipeline.inference_service = FakeInferenceService()

    result = asyncio.run(app.chicken_threat_pipeline.run_once())

    assert result.success is True
    assert published[0] == (
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
    usage_topic, usage_payload = published[1]
    assert usage_topic == "loxone/usage/camera-inference"
    assert usage_payload["event"] == "camera_inference"
    assert usage_payload["source"] == "esp32cam.local"
    assert usage_payload["success"] is True
    assert usage_payload["level"] == "medium"
    assert usage_payload["score"] == 0.675
    assert usage_payload["detection_count"] == 1
    assert "timestamp" in usage_payload
