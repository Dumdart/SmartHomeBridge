import asyncio
from collections.abc import Callable
from typing import Any

from smart_home_bridge.bridge_devices.runtime import BridgeDeviceRuntime
from smart_home_bridge.composition import BridgeComposition, create_bridge_composition
from smart_home_bridge.config import MqttConfig, app_config, load_config
from smart_home_bridge.infrastructure.mqtt.mqtt_client import MqttClient
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttAdapter


class App:
    def __init__(
        self,
        config: app_config,
        mqtt_client_factory: Callable[[MqttConfig], MqttAdapter] = MqttClient,
        composition_factory: Callable[[app_config], BridgeComposition] = create_bridge_composition,
    ):
        self.name = "SmartHomeBridge"
        self.config = config

        self.composition = composition_factory(config)
        self.http_gate = self.composition.http_gate

        self.device_runtimes = tuple(
            device_composition.create_runtime(mqtt_client_factory)
            for device_composition in self.composition.device_compositions
        )
        self._handles = self._collect_handles(self.device_runtimes)
        self._handles.update(self.composition.handles)

        for name, value in self._handles.items():
            setattr(self, name, value)

    async def start(self):
        print(f"Starting {self.name} application\n")

        for runtime in self.device_runtimes:
            await runtime.start()

        await asyncio.Event().wait()

    async def stop(self):
        try:
            print(f"\nStopping {self.name} application.")
            for runtime in reversed(self.device_runtimes):
                await runtime.stop()

        except Exception as e:
            print(f"Error during shutdown: {e}")

    def _collect_handles(
        self,
        device_runtimes: tuple[BridgeDeviceRuntime, ...],
    ) -> dict[str, Any]:
        handles: dict[str, Any] = {}
        for runtime in device_runtimes:
            handles.update(runtime.handles)
        return handles


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
