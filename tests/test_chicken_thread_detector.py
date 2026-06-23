import asyncio
import json
from types import SimpleNamespace

from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    DangerScorer,
    chicken_thread_detector,
    chicken_thread_detector_controller,
    chicken_thread_detector_mqtt_callbacks,
)
from smart_home_bridge.config import DoorApiConfig, HttpConfig, MqttConfig, app_config
from smart_home_bridge.models import Detection, ThreatLevel


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


def test_mqtt_callback_ignores_published_assessment_payloads():
    detector = chicken_thread_detector(2, "thread-detector")
    controller = chicken_thread_detector_controller(detector)
    callbacks = chicken_thread_detector_mqtt_callbacks(controller)
    payload = json.dumps({"level": "high", "score": 0.75})
    message = SimpleNamespace(topic="loxone/chicken-thread-detector", payload=payload.encode())

    callbacks.on_message(None, None, message)

    assert detector.assessment.level == ThreatLevel.NONE


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
    app = App(config)
    published = []

    class FakeMqttClient:
        async def publish(self, topic, payload, on_publish=None):
            published.append((topic, json.loads(payload)))

    app.chicken_thread_detector_mqtt_gate.client = FakeMqttClient()

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
