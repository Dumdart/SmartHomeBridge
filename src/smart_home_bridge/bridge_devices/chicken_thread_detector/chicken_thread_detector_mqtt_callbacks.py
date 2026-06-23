import asyncio
import json

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.infrastructure.mqtt.mqtt_callbacks import mqtt_callbacks
from smart_home_bridge.models import DetectionFrame


class chicken_thread_detector_mqtt_callbacks(mqtt_callbacks):
    def __init__(self, detector_controller: chicken_thread_detector_controller):
        super().__init__()
        self.detector_controller = detector_controller

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode().strip()
            print(f"Received message on topic {msg.topic}: {payload}")

            if payload.startswith("{"):
                parsed_payload = json.loads(payload)
                if isinstance(parsed_payload, dict) and "detections" in parsed_payload:
                    frame = DetectionFrame.from_mapping(parsed_payload)
                    return asyncio.run(self.detector_controller.score_frame(frame))

                return None

            return asyncio.run(self.detector_controller.excecute_command(payload))

        except Exception as e:
            print(f"Message is not a detector payload or command: {e}")

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("CONNACK received with code %s." % rc)

    def on_disconnect(self, client, userdata, rc, properties=None):
        print("Disconnected with code %s." % rc)

    def on_publish(self, client, userdata, mid, properties=None):
        print("Publish: " + str(mid))

    def on_unsubscribe(self, client, userdata, mid, properties=None):
        print("Unsubscribed: " + str(mid))
