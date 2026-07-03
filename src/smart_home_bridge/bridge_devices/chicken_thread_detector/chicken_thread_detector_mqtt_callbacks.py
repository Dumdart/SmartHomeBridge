from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_message import (
    handle_chicken_thread_detector_mqtt_message,
)
from smart_home_bridge.bridge_devices.mqtt_callbacks import BridgeDeviceMqttCallbacks


class chicken_thread_detector_mqtt_callbacks(BridgeDeviceMqttCallbacks):
    def __init__(self, detector_controller: chicken_thread_detector_controller):
        self.detector_controller = detector_controller
        super().__init__(
            lambda topic, payload: handle_chicken_thread_detector_mqtt_message(
                topic,
                payload,
                self.detector_controller,
            )
        )
