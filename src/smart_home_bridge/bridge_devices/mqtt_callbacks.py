from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from smart_home_bridge.infrastructure.mqtt.mqtt_callbacks import mqtt_callbacks

MqttMessageHandler = Callable[[str, bytes], Awaitable[object]]


class BridgeDeviceMqttCallbacks(mqtt_callbacks):
    def __init__(
        self,
        message_handler: MqttMessageHandler,
        ignore_retained: bool = True,
    ):
        super().__init__()
        self.message_handler = message_handler
        self.ignore_retained = ignore_retained

    def on_message(self, client, userdata, msg):
        if self.ignore_retained and getattr(msg, "retain", False):
            print(f"Ignoring retained message on topic {msg.topic}.")
            return None

        try:
            return asyncio.run(self.message_handler(msg.topic, msg.payload))
        except Exception as exc:
            print(f"MQTT message handling failed on topic {msg.topic}: {exc}")
            return None

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("CONNACK received with code %s." % rc)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code=None, properties=None):
        code = reason_code if reason_code is not None else disconnect_flags
        print("Disconnected with code %s." % code)

    def on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        print("Publish: " + str(mid))

    def on_unsubscribe(self, client, userdata, mid, properties=None):
        print("Unsubscribed: " + str(mid))
