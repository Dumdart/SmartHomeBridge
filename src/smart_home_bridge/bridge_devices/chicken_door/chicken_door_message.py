from __future__ import annotations

from dataclasses import dataclass

from smart_home_bridge.bridge_devices.chicken_door.door_controller import door_controller


@dataclass(frozen=True)
class chicken_door_message:
    topic: str
    command: str

    @classmethod
    def from_mqtt_payload(cls, topic: str, payload: bytes) -> chicken_door_message:
        return cls(topic, payload.decode().strip())

    async def handle(self, controller: door_controller):
        print(f"Received message on topic {self.topic}: {self.command}")
        return await controller.excecute_command(self.command)


async def handle_chicken_door_mqtt_message(
    topic: str,
    payload: bytes,
    controller: door_controller,
):
    try:
        message = chicken_door_message.from_mqtt_payload(topic, payload)
        return await message.handle(controller)
    except Exception as e:
        print(f"Message is not a command: {e}")
