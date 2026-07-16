import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from smart_home_bridge.bridge_devices.chicken_door.door_controller import door_controller
from smart_home_bridge.bridge_devices.chicken_door.door_status import door_status

logger = logging.getLogger(__name__)


class DoorStatePollingService:
    def __init__(
        self,
        controller: door_controller,
        poll_interval_seconds: float,
        status_file_path: str | Path | None = None,
    ):
        self.controller = controller
        self.poll_interval_seconds = poll_interval_seconds
        self.status_file_path = (
            Path(status_file_path) if status_file_path is not None else None
        )
        self._last_status: door_status | None = None
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run_once(self) -> door_status | None:
        # Check every successful poll is published as an MQTT heartbeat.
        status = await self.controller.poll_state(None)
        if status is not None:
            if status != self._last_status:
                await self._write_status(status)
            self._last_status = status
        return status

    async def _write_status(self, status: door_status):
        if self.status_file_path is None:
            return

        try:
            await asyncio.to_thread(
                _write_status_file,
                self.status_file_path,
                status,
            )
        except Exception as exc:
            logger.warning("Could not update door polling UI status: %s", exc)

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


def _write_status_file(path: Path, status: door_status):
    path.parent.mkdir(parents=True, exist_ok=True)
    values = asdict(status)
    values["position"] = status.position.value
    values["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(values, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary_path.replace(path)
