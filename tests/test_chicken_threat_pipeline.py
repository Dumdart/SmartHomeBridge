import asyncio

from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatDetectionPipeline,
)
from smart_home_bridge.core.command import command_result
from smart_home_bridge.models import DetectionFrame


class FakeCameraClient:
    def __init__(self, image_bytes=b"\xff\xd8frame", error=None):
        self.image_bytes = image_bytes
        self.error = error
        self.fetch_count = 0

    def fetch_jpeg(self):
        self.fetch_count += 1
        if self.error:
            raise self.error

        return self.image_bytes

    def health(self):
        return self.error is None


class FakeInferenceService:
    def __init__(self, frame=None, error=None):
        self.frame = frame or DetectionFrame(source="fake-camera")
        self.error = error
        self.calls = []

    def detect(self, image_bytes, source=None):
        self.calls.append((image_bytes, source))
        if self.error:
            raise self.error

        return self.frame


class FakeDetectorController:
    def __init__(self):
        self.frames = []

    async def score_frame(self, frame):
        self.frames.append(frame)
        return command_result(data=frame)


def test_pipeline_fetches_infers_scores_and_publishes_assessment():
    camera = FakeCameraClient()
    frame = DetectionFrame(source="esp32cam")
    inference = FakeInferenceService(frame=frame)
    controller = FakeDetectorController()
    pipeline = ChickenThreatDetectionPipeline(
        camera_client=camera,
        inference_service=inference,
        detector_controller=controller,
        poll_interval_seconds=10,
        source="esp32cam",
    )

    result = asyncio.run(pipeline.run_once())

    assert result.success is True
    assert camera.fetch_count == 1
    assert inference.calls == [(b"\xff\xd8frame", "esp32cam")]
    assert controller.frames == [frame]


def test_pipeline_does_not_score_when_camera_fetch_fails():
    camera = FakeCameraClient(error=RuntimeError("camera down"))
    inference = FakeInferenceService()
    controller = FakeDetectorController()
    pipeline = ChickenThreatDetectionPipeline(
        camera_client=camera,
        inference_service=inference,
        detector_controller=controller,
        poll_interval_seconds=10,
    )

    try:
        asyncio.run(pipeline.run_once())
    except RuntimeError as exc:
        assert str(exc) == "camera down"
    else:
        raise AssertionError("Expected camera failure to be raised")

    assert inference.calls == []
    assert controller.frames == []


def test_pipeline_does_not_score_when_inference_fails():
    camera = FakeCameraClient()
    inference = FakeInferenceService(error=RuntimeError("model failed"))
    controller = FakeDetectorController()
    pipeline = ChickenThreatDetectionPipeline(
        camera_client=camera,
        inference_service=inference,
        detector_controller=controller,
        poll_interval_seconds=10,
    )

    try:
        asyncio.run(pipeline.run_once())
    except RuntimeError as exc:
        assert str(exc) == "model failed"
    else:
        raise AssertionError("Expected inference failure to be raised")

    assert controller.frames == []


def test_pipeline_start_and_stop_manage_background_task():
    async def exercise_pipeline():
        pipeline = ChickenThreatDetectionPipeline(
            camera_client=FakeCameraClient(),
            inference_service=FakeInferenceService(),
            detector_controller=FakeDetectorController(),
            poll_interval_seconds=60,
        )

        await pipeline.start()
        assert pipeline._task is not None
        await pipeline.stop()
        assert pipeline._task is None

    asyncio.run(exercise_pipeline())
