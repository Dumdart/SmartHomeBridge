import asyncio
import inspect
from collections.abc import Awaitable, Callable

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.inference import (
    ChickenThreatInferenceService,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.scan import ChickenThreatScanService
from smart_home_bridge.core.command import command_result
from smart_home_bridge.infrastructure.camera import CameraClientInterface

CameraInferenceUsageReporter = Callable[
    [str | None, bool, str | None, float | None, int | None],
    Awaitable[None] | None,
]


class ChickenThreatDetectionPipeline:
    def __init__(
        self,
        camera_client: CameraClientInterface,
        inference_service: ChickenThreatInferenceService,
        detector_controller: chicken_thread_detector_controller,
        poll_interval_seconds: float,
        source: str | None = None,
        usage_reporter: CameraInferenceUsageReporter | None = None,
    ):
        self.scan_service = ChickenThreatScanService(
            camera_client=camera_client,
            inference_service=inference_service,
            detector_controller=detector_controller,
            source=source,
        )
        self.poll_interval_seconds = poll_interval_seconds
        self.usage_reporter = usage_reporter
        self._task: asyncio.Task | None = None

    @property
    def camera_client(self) -> CameraClientInterface:
        return self.scan_service.camera_client

    @camera_client.setter
    def camera_client(self, camera_client: CameraClientInterface):
        self.scan_service.camera_client = camera_client

    @property
    def inference_service(self) -> ChickenThreatInferenceService:
        return self.scan_service.inference_service

    @inference_service.setter
    def inference_service(self, inference_service: ChickenThreatInferenceService):
        self.scan_service.inference_service = inference_service

    @property
    def detector_controller(self) -> chicken_thread_detector_controller:
        return self.scan_service.detector_controller

    @detector_controller.setter
    def detector_controller(self, detector_controller: chicken_thread_detector_controller):
        self.scan_service.detector_controller = detector_controller

    @property
    def source(self) -> str | None:
        return self.scan_service.source

    @source.setter
    def source(self, source: str | None):
        self.scan_service.source = source

    async def run_once(self) -> command_result:
        scan_result = await self.scan_service.scan_once()
        await self._report_usage(scan_result)
        return scan_result.score_result

    async def _report_usage(self, scan_result):
        if self.usage_reporter is None:
            return

        report_result = self.usage_reporter(
            scan_result.frame.source or self.source,
            scan_result.score_result.success,
            scan_result.assessment.level.value,
            scan_result.assessment.score,
            scan_result.assessment.detection_count,
        )
        if inspect.isawaitable(report_result):
            await report_result

    async def start(self):
        if self._task is not None and not self._task.done():
            return

        if not await asyncio.to_thread(self.camera_client.health):
            print("Chicken threat detection pipeline not started: camera health check failed.")
            return

        print("Chicken threat detection camera health check passed.")
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
