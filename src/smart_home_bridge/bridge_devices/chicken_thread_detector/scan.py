import asyncio
from dataclasses import dataclass

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.inference import (
    ChickenThreatInferenceService,
)
from smart_home_bridge.core.command import command_result
from smart_home_bridge.infrastructure.camera import CameraClientInterface
from smart_home_bridge.models import DangerAssessment, DetectionFrame


@dataclass(frozen=True)
class ChickenThreatScanResult:
    image_bytes: bytes
    frame: DetectionFrame
    assessment: DangerAssessment
    score_result: command_result


class ChickenThreatScanService:
    def __init__(
        self,
        camera_client: CameraClientInterface,
        inference_service: ChickenThreatInferenceService,
        detector_controller: chicken_thread_detector_controller,
        source: str | None = None,
    ):
        self.camera_client = camera_client
        self.inference_service = inference_service
        self.detector_controller = detector_controller
        self.source = source

    async def scan_once(self) -> ChickenThreatScanResult:
        image_bytes = await asyncio.to_thread(self.camera_client.fetch_jpeg)
        frame = await asyncio.to_thread(
            self.inference_service.detect,
            image_bytes,
            self.source,
        )
        result = await self.detector_controller.score_frame(frame)
        assessment = result.data

        if not isinstance(assessment, DangerAssessment):
            raise RuntimeError("Threat detector did not return a danger assessment.")

        return ChickenThreatScanResult(
            image_bytes=image_bytes,
            frame=frame,
            assessment=assessment,
            score_result=result,
        )
