import asyncio
import logging

from smart_home_bridge.bridge_devices.chicken_door.door_controller import door_controller
from smart_home_bridge.bridge_devices.chicken_door.door_status import door_status

logger = logging.getLogger(__name__)


class DoorStatePollingService:
    def __init__(
        self,
        controller: door_controller,
        poll_interval_seconds: float,
    ):
        self.controller = controller
        self.poll_interval_seconds = poll_interval_seconds
        self._last_status: door_status | None = None
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run_once(self) -> door_status | None:
        status = await self.controller.poll_state(self._last_status)
        if status is not None:
            self._last_status = status
        return status

    async def start(self):
        if self.is_running:
            return

        logger.info(
            "Polling Omlet door state every %s seconds.",
            self.poll_interval_seconds,
        )
        self._task = asyncio.create_task(self._poll())

    async def stop(self):
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _poll(self):
        while True:
            await self.run_once()
            await asyncio.sleep(self.poll_interval_seconds)
