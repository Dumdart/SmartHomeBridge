import asyncio

from smart_home_bridge.config import MqttConfig
from smart_home_bridge.infrastructure.mqtt.mqtt_callbacks import mqtt_callbacks
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttGate


def test_mqtt_gate_publishes_to_built_topic_through_injected_client():
    client = FakeMqttClient()
    callbacks = FakeMqttCallbacks()
    gate = MqttGate(_mqtt_config(), callbacks, "chicken-door", client=client)

    asyncio.run(gate.publish("open"))

    assert client.published == [("loxone/chicken-door", "open", callbacks.on_publish)]


def test_mqtt_gate_subscribes_and_registers_message_callback_through_injected_client():
    client = FakeMqttClient()
    callbacks = FakeMqttCallbacks()
    gate = MqttGate(_mqtt_config(), callbacks, "/chicken-door/", client=client)

    asyncio.run(gate.subscribe())

    assert client.subscribed == [("loxone/chicken-door", callbacks.on_subscribe)]
    assert client.message_callbacks == [("loxone/chicken-door", callbacks.on_message)]


class FakeMqttClient:
    def __init__(self):
        self.published = []
        self.subscribed = []
        self.message_callbacks = []

    async def publish(self, topic, payload, on_publish=None):
        self.published.append((topic, payload, on_publish))

    async def subscribe(self, topic, on_subscribe=None):
        self.subscribed.append((topic, on_subscribe))

    def message_callback_add(self, topic, callback):
        self.message_callbacks.append((topic, callback))


class FakeMqttCallbacks(mqtt_callbacks):
    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        pass

    def on_connect(self, client, userdata, flags, rc, properties=None):
        pass

    def on_disconnect(self, client, userdata, rc, properties=None):
        pass

    def on_publish(self, client, userdata, mid, properties=None):
        pass

    def on_unsubscribe(self, client, userdata, mid, properties=None):
        pass

    def on_message(self, client, userdata, msg):
        pass


def _mqtt_config() -> MqttConfig:
    return MqttConfig(
        host="mqtt.local",
        port=8883,
        username="user",
        password="password",
        base_topic="loxone",
    )
