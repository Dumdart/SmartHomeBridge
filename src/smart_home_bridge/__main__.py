import asyncio
from collections.abc import Callable

from smart_home_bridge.composition import (
    CHICKEN_DOOR_TOPIC,
    CHICKEN_THREAD_DETECTOR_TOPIC,
    create_bridge_composition,
)
from smart_home_bridge.config import MqttConfig, app_config, load_config
from smart_home_bridge.infrastructure.mqtt.mqtt_client import MqttClient
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttAdapter, MqttGate
from smart_home_bridge.bridge_devices.chicken_door import (
    chicken_door_mqtt_callbacks,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    chicken_thread_detector_mqtt_callbacks,
)


class App:
    def __init__(
        self,
        config: app_config,
        mqtt_client_factory: Callable[[MqttConfig], MqttAdapter] = MqttClient,
    ):
        self.name = "SmartHomeBridge"
        self.config = config        
        
        self.composition = create_bridge_composition(config)
        self.door = self.composition.door
        self.http_gate = self.composition.http_gate
        self.door_controller = self.composition.door_controller
        self.thread_detector = self.composition.threat_detector
        self.thread_model_config = self.composition.threat_model_config
        self.thread_detector_controller = self.composition.threat_detector_controller

        self.chicken_door_mqtt_gate = MqttGate(
            config.mqtt,
            chicken_door_mqtt_callbacks(self.door_controller),
            CHICKEN_DOOR_TOPIC,
            client=mqtt_client_factory(config.mqtt),
        )
        self.door_controller.set_publishable(self.chicken_door_mqtt_gate.publish)

        self.chicken_thread_detector_mqtt_gate = MqttGate(
            config.mqtt,
            chicken_thread_detector_mqtt_callbacks(self.thread_detector_controller),
            CHICKEN_THREAD_DETECTOR_TOPIC,
            client=mqtt_client_factory(config.mqtt),
        )
        self.thread_detector_controller.set_publishable(self.chicken_thread_detector_mqtt_gate.publish)
        self.chicken_threat_pipeline = self.composition.create_chicken_threat_pipeline()

    async def start(self):           
        print(f"Starting {self.name} application\n")

        await self.chicken_door_mqtt_gate.start()
        await self.chicken_door_mqtt_gate.subscribe()
        await self.chicken_thread_detector_mqtt_gate.start()
        await self.chicken_thread_detector_mqtt_gate.subscribe()
        if self.chicken_threat_pipeline is not None:
            await self.chicken_threat_pipeline.start()

        await asyncio.Event().wait()

    async def stop(self):
        try:
            print(f"\nStopping {self.name} application.")
            if self.chicken_threat_pipeline is not None:
                await self.chicken_threat_pipeline.stop()
            await self.chicken_door_mqtt_gate.stop()
            await self.chicken_thread_detector_mqtt_gate.stop()

        except Exception as e:
            print(f"Error during shutdown: {e}")

async def main():
    app_config = load_config()
    application = App(app_config)

    try:
        await application.start()
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        await application.stop()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
