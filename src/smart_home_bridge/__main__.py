import asyncio
from loxone_bridge.config import app_config, load_config
from loxone_bridge.infrastructure.api.http_gate import HttpGate
from loxone_bridge.infrastructure.mqtt.mqtt_gate import MqttGate
from loxone_bridge.bridge_devices.chicken_door import (
    chicken_door,
    chicken_door_mqtt_callbacks,
    door_controller,
    door_position,
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

    async def start(self):           
        print(f"Starting {self.name} application\n")

        await self.chicken_door_mqtt_gate.start()
        await self.chicken_door_mqtt_gate.subscribe()

        await asyncio.Event().wait()

    async def stop(self):
        try:
            print(f"\nStopping {self.name} application.")
            await self.chicken_door_mqtt_gate.stop()

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
