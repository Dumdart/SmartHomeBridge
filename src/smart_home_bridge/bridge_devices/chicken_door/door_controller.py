import asyncio
import inspect
import logging
import threading
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from smart_home_bridge.bridge_devices.chicken_door.chicken_door import chicken_door, door_position
from smart_home_bridge.bridge_devices.chicken_door.door_gateway import DoorGateway
from smart_home_bridge.bridge_devices.chicken_door.door_status import door_status
from smart_home_bridge.core import device_controller
from smart_home_bridge.core.command import Publishable, command, command_result


OPEN_DOOR_COMMAND = "open_door"
CLOSE_DOOR_COMMAND = "close_door"
STOP_DOOR_COMMAND = "stop_door"
GET_DOOR_STATE_COMMAND = "get_door_state"

logger = logging.getLogger(__name__)
DoorUsageReporter = Callable[[str, bool, door_position | None], Awaitable[None] | None]


class door_command(command):
    def __init__(
        self,
        door: chicken_door,
        publishable: Publishable | None = None,
        gateway: DoorGateway | None = None,
    ):
        super().__init__(publishable)
        self.door = door
        self.gateway = gateway

    async def publish_status(self, status: door_status):
        await self.publish(status)

    def apply_status(self, status: door_status) -> door_position:
        self.door.set_device_state(status.position)
        return self.door.position

    async def execute_gateway(self, operation):
        try:
            status = await asyncio.to_thread(operation)
            state = self.apply_status(status)
            await self.publish_status(status)
            return command_result(data=state)
        except Exception:
            logger.exception("Door gateway command failed.")
            return command_result(data=self.door.position, success=False)


class open_door_command(door_command):
    async def excecute(self):
        if self.gateway is not None:
            return await self.execute_gateway(self.gateway.open)

        state = self.door.open()
        await self.publish_status(door_status(state))
        return command_result(data=state)


class close_door_command(door_command):
    async def excecute(self):
        if self.gateway is not None:
            return await self.execute_gateway(self.gateway.close)

        state = self.door.close()
        await self.publish_status(door_status(state))
        return command_result(data=state)


class stop_door_command(door_command):
    async def excecute(self):
        if self.gateway is not None:
            return await self.execute_gateway(self.gateway.stop)

        state = self.door.stop()
        await self.publish_status(door_status(state))
        return command_result(data=state)


class get_door_state_command(door_command):
    async def excecute(self):
        if self.gateway is not None:
            return await self.execute_gateway(self.gateway.get_state)

        state = self.door.get_device_state()
        await self.publish_status(door_status(state))
        return command_result(data=state)


COMMANDS: dict[str, type[door_command]] = {
    OPEN_DOOR_COMMAND: open_door_command,
    CLOSE_DOOR_COMMAND: close_door_command,
    STOP_DOOR_COMMAND: stop_door_command,
    GET_DOOR_STATE_COMMAND: get_door_state_command,
}


class door_controller(device_controller):
    def __init__(
        self,
        device: chicken_door,
        gateway: DoorGateway | None = None,
        publishable: Publishable | None = None,
        usage_reporter: DoorUsageReporter | None = None,
    ):
        self.device = device
        self.gateway = gateway
        self.publishable = publishable
        self.usage_reporter = usage_reporter
        self._operation_lock = threading.Lock()

    def set_publishable(self, publishable: Publishable | None):
        self.publishable = publishable

    def set_usage_reporter(self, usage_reporter: DoorUsageReporter | None):
        self.usage_reporter = usage_reporter

    def get_command(self, command: str) -> command:
        command_type = COMMANDS.get(command)
        if command_type is None:
            raise ValueError(f"Command {command} not found for device {self.device.name}.")

        return command_type(self.device, self.publishable, self.gateway)

    async def excecute_command(self, command: str) -> command_result:
        async with self._serialized_operation():
            command_instance = self.get_command(command)
            result = await command_instance.excecute()
        await self._report_usage(command, result)
        return result

    async def poll_state(
        self,
        previous_status: door_status | None,
    ) -> door_status | None:
        async with self._serialized_operation():
            try:
                if self.gateway is None:
                    status = door_status(self.device.get_device_state())
                else:
                    status = await asyncio.to_thread(self.gateway.get_state)

                self.device.set_device_state(status.position)
                if status != previous_status and self.publishable is not None:
                    publish_result = self.publishable(status)
                    if inspect.isawaitable(publish_result):
                        await publish_result
                return status
            except Exception:
                logger.exception("Door state poll failed.")
                return None

    @asynccontextmanager
    async def _serialized_operation(self):
        while not self._operation_lock.acquire(blocking=False):
            await asyncio.sleep(0.01)
        try:
            yield
        finally:
            self._operation_lock.release()

    async def _report_usage(self, command: str, result: command_result):
        if self.usage_reporter is None:
            return

        position = result.data if isinstance(result.data, door_position) else None
        report_result = self.usage_reporter(command, result.success, position)
        if inspect.isawaitable(report_result):
            await report_result
