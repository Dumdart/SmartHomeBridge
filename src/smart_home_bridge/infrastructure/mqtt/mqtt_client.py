from collections.abc import Callable

import paho.mqtt.client as paho
from paho import mqtt


from smart_home_bridge.config import MqttConfig


class MqttClient:
    def __init__(self, mqtt_config: MqttConfig):
        self.config = mqtt_config
        self.client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)

    async def connect(self, on_connect: Callable | None = None):
        if on_connect:
            self.client.on_connect = on_connect

        self.client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
        self.client.username_pw_set(self.config.username, self.config.password)

        self.client.connect(self.config.host, self.config.port)
        self.client.loop_start()

    async def disconnect(self, on_disconnect: Callable | None = None):
        if on_disconnect:
            self.client.on_disconnect = on_disconnect

        self.client.disconnect()
        self.client.loop_stop()

    async def publish(self, topic, payload, on_publish: Callable | None = None):
        if on_publish:
            self.client.on_publish = on_publish

        result = self.client.publish(topic, payload, qos=1)
        result.wait_for_publish()

        if result.rc != paho.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Failed to publish MQTT message: {paho.error_string(result.rc)}")

    async def subscribe(self, topic, on_subscribe: Callable | None = None):
        if on_subscribe:
            self.client.on_subscribe = on_subscribe

        self.client.subscribe(topic)

    async def unsubscribe(self, topic, on_unsubscribe: Callable | None = None):
        if on_unsubscribe:
            self.client.on_unsubscribe = on_unsubscribe

        self.client.unsubscribe(topic)

    def message_callback_add(self, topic, callback):
        self.client.message_callback_add(topic, callback)
