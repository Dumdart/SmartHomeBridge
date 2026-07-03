from smart_home_bridge.bridge_devices.chicken_door.door_controller import door_controller
from smart_home_bridge.bridge_devices.chicken_door.chicken_door_message import (
    handle_chicken_door_mqtt_message,
)
from smart_home_bridge.bridge_devices.mqtt_callbacks import BridgeDeviceMqttCallbacks


class chicken_door_mqtt_callbacks(BridgeDeviceMqttCallbacks):
    def __init__(self, door_controller: door_controller):
        self.door_controller = door_controller
        super().__init__(
            lambda topic, payload: handle_chicken_door_mqtt_message(
                topic,
                payload,
                self.door_controller,
            )
        )
