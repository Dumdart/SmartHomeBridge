from loxone_bridge.bridge_devices.chicken_door.chicken_door import chicken_door, door_position
from loxone_bridge.core import device_controller
from loxone_bridge.core.command import Publishable, command, command_result
from loxone_bridge.infrastructure.api.http_gate import HttpGateInterface


class door_controller(device_controller):
    def __init__(self, device: chicken_door, http_gate: HttpGateInterface, publishable: Publishable | None = None):
        self.device = device
        self.http_gate = http_gate
        self.publishable = publishable

    def set_publishable(self, publishable: Publishable | None):
        self.publishable = publishable

    def get_command(self, command: str) -> command: 
        match command:
            case "open_door":
                return open_door_command(self.device, self.http_gate, self.publishable)
            case "close_door":
                return close_door_command(self.device, self.http_gate, self.publishable)
            case "stop_door":
                return stop_door_command(self.device, self.http_gate, self.publishable)
            case "get_door_state":
                return get_door_state_command(self.device, self.http_gate, self.publishable)
            case _:                
                raise ValueError(f"Command {command} not found for device {self.device.name}.")

    async def excecute_command(self, command: str) -> command_result:
        command_instance = self.get_command(command)
        if not command_instance:
            print(f"Command {command} not found for device {self.device.name}.")

        result = await command_instance.excecute()
        return result


class door_command(command):
    def __init__(self, door: chicken_door, http_gate: HttpGateInterface, publishable: Publishable | None = None):
        super().__init__(publishable)
        self.door = door
        self.http_gate = http_gate


class open_door_command(door_command):
    async def excecute(self):
        if self.door.position == door_position.CLOSED:
            self.door.position = door_position.OPEN
            print(f"{self.door.name} is now open.")
        else:
            print(f"{self.door.name} is already open.")

        await self.publish(self.door.position.value)
        return command_result(data=self.door.position)


class close_door_command(door_command):
    async def excecute(self):
        if self.door.position == door_position.OPEN:
            self.door.position = door_position.CLOSED
            print(f"{self.door.name} is now closed.")
        else:
            print(f"{self.door.name} is already closed.")

        await self.publish(self.door.position.value)
        return command_result(data=self.door.position)


class stop_door_command(door_command):
    async def excecute(self):
        await self.publish(self.door.position.value)
        return command_result(data=self.door.position)


class get_door_state_command(door_command):
    async def excecute(self):
        state = self.door.get_device_state()
        await self.publish(state.value)
        return command_result(data=state)
