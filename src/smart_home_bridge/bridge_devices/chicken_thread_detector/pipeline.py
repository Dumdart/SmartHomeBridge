import asyncio

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.inference import (
    ChickenThreatInferenceService,
)
from smart_home_bridge.core.command import command_result
from smart_home_bridge.infrastructure.camera import CameraClientInterface


class ChickenThreatDetectionPipeline:
    def __init__(
        self,
        camera_client: CameraClientInterface,
        inference_service: ChickenThreatInferenceService,
        detector_controller: chicken_thread_detector_controller,
        poll_interval_seconds: float,
        source: str | None = None,
    ):
        self.camera_client = camera_client
        self.inference_service = inference_service
        self.detector_controller = detector_controller
        self.poll_interval_seconds = poll_interval_seconds
        self.source = source
        self._task: asyncio.Task | None = None

    async def run_once(self) -> command_result:
        image_bytes = await asyncio.to_thread(self.camera_client.fetch_jpeg)
        frame = await asyncio.to_thread(self.inference_service.detect, image_bytes, self.source)
        return await self.detector_controller.score_frame(frame)

    async def start(self):
        if self._task is not None and not self._task.done():
            return

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
            try:
                await self.run_once()
            except Exception as exc:
                print(f"Chicken threat detection poll failed: {exc}")

            await asyncio.sleep(self.poll_interval_seconds)
