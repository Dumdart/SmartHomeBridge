import asyncio
import json

from smart_home_bridge.services.mqtt_usage_reporter import MqttUsageReporter


def test_reports_chicken_door_usage_event_to_mqtt():
    published = []

    async def publish(topic, payload, retain=False):
        published.append((topic, json.loads(payload), retain))

    reporter = MqttUsageReporter(publish, "smart-home-bridge")

    asyncio.run(
        reporter.report_chicken_door(
            "open_door",
            True,
            "open",
            topic_name="usage/coop-door",
        )
    )

    topic, payload, retain = published[0]
    assert topic == "smart-home-bridge/usage/coop-door"
    assert retain is False
    assert payload["event"] == "chicken_door_command"
    assert payload["command"] == "open_door"
    assert payload["success"] is True
    assert payload["position"] == "open"
    assert "timestamp" in payload


def test_reports_camera_inference_usage_event_to_mqtt():
    published = []

    async def publish(topic, payload, retain=False):
        published.append((topic, json.loads(payload), retain))

    reporter = MqttUsageReporter(publish, "smart-home-bridge")

    asyncio.run(reporter.report_camera_inference("esp32cam", True, "medium", 0.675, 1))

    topic, payload, retain = published[0]
    assert topic == "smart-home-bridge/usage/camera-inference"
    assert retain is False
    assert payload["event"] == "camera_inference"
    assert payload["source"] == "esp32cam"
    assert payload["success"] is True
    assert payload["level"] == "medium"
    assert payload["score"] == 0.675
    assert payload["detection_count"] == 1
    assert "timestamp" in payload


def test_usage_publish_failure_does_not_raise():
    async def publish(topic, payload, retain=False):
        raise RuntimeError("broker unavailable")

    reporter = MqttUsageReporter(publish, "smart-home-bridge")

    asyncio.run(
        reporter.report_chicken_door(
            "open_door",
            True,
            "open",
            topic_name="usage/door",
        )
    )
