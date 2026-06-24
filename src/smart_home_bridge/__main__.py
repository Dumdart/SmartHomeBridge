import asyncio
from smart_home_bridge.config import app_config, load_config
from smart_home_bridge.infrastructure.api.http_gate import HttpGate
from smart_home_bridge.infrastructure.camera import CameraClient
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttGate
from smart_home_bridge.bridge_devices.chicken_door import (
    chicken_door,
    chicken_door_mqtt_callbacks,
    door_controller,
    door_position,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatDetectionPipeline,
    ChickenThreatInferenceService,
    DangerScorer,
    LocalChickenThreadDetector,
    chicken_thread_detector,
    chicken_thread_detector_controller,
    chicken_thread_detector_mqtt_callbacks,
    default_model_config,
)


class App:
    def __init__(self, config: app_config):
        self.name = "LoxoneBridge" 
        self.config = config        
        
        # Define devices here
        self.door = chicken_door(1, "door", door_position.UNKNOWN)
        self.http_gate = HttpGate(config.http)
        self.door_controller = door_controller(self.door, self.http_gate)
        self.chicken_door_mqtt_gate = MqttGate(config.mqtt, chicken_door_mqtt_callbacks(self.door_controller), "chicken-door")
        self.door_controller.set_publishable(self.chicken_door_mqtt_gate.publish)

        self.thread_detector = chicken_thread_detector(2, "chicken_thread_detector")
        self.thread_model_config = default_model_config(config.chicken_threat.model_path)
        self.thread_detector_controller = chicken_thread_detector_controller(
            self.thread_detector,
            danger_scorer=DangerScorer(self.thread_model_config),
        )
        self.chicken_thread_detector_mqtt_gate = MqttGate(
            config.mqtt,
            chicken_thread_detector_mqtt_callbacks(self.thread_detector_controller),
            "chicken-thread-detector",
        )
        self.thread_detector_controller.set_publishable(self.chicken_thread_detector_mqtt_gate.publish)
        self.chicken_threat_pipeline = self._build_chicken_threat_pipeline()

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

    def _build_chicken_threat_pipeline(self) -> ChickenThreatDetectionPipeline | None:
        if not self.config.chicken_threat.enabled:
            return None

        camera_client = CameraClient(self.config.camera)
        inference_service = ChickenThreatInferenceService(
            LocalChickenThreadDetector(self.thread_model_config)
        )
        return ChickenThreatDetectionPipeline(
            camera_client=camera_client,
            inference_service=inference_service,
            detector_controller=self.thread_detector_controller,
            poll_interval_seconds=self.config.chicken_threat.poll_interval_seconds,
            source=self.config.camera.host,
        )


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
