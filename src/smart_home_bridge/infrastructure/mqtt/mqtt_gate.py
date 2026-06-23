from collections.abc import Callable

from smart_home_bridge.config import MqttConfig
from smart_home_bridge.infrastructure.mqtt.mqtt_callbacks import mqtt_callbacks
from smart_home_bridge.infrastructure.mqtt.mqtt_client import MqttClient


class MqttGate:
    def __init__(self, mqtt_config: MqttConfig, mqtt_callbacks: mqtt_callbacks, topic: str | None = None):
        self.client = MqttClient(mqtt_config)

        self.config = mqtt_config
        self.mqtt_callbacks = mqtt_callbacks
        self.topic = self._build_topic(mqtt_config.base_topic, topic)

    async def start(self):
        await self.client.connect(self.callbacks("on_connect", self.mqtt_callbacks))

    async def stop(self):
        await self.client.disconnect(self.callbacks("on_disconnect", self.mqtt_callbacks))

    async def publish(self, payload):
        await self.client.publish(self.topic, payload, self.callbacks("on_publish", self.mqtt_callbacks))

    async def subscribe(self):
        await self.client.subscribe(self.topic, self.callbacks("on_subscribe", self.mqtt_callbacks))
        self.client.message_callback_add(self.topic, self.callbacks("on_message", self.mqtt_callbacks))

    async def unsubscribe(self):
        await self.client.unsubscribe(self.topic, self.callbacks("on_unsubscribe", self.mqtt_callbacks))

    def callbacks(self, event: str, mqtt_callbacks: mqtt_callbacks) -> Callable:
        return getattr(mqtt_callbacks, event)

    def _build_topic(self, base_topic: str, topic: str | None = None) -> str:
        if topic is None or topic.strip() == "":
            return base_topic

        return f"{base_topic.rstrip('/')}/{topic.strip('/')}"

