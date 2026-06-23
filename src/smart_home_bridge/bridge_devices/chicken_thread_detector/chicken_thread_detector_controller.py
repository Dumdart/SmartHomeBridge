import inspect

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector import (
    chicken_thread_detector,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.danger_scoring import DangerScorer
from smart_home_bridge.core import device_controller
from smart_home_bridge.core.command import Publishable, command, command_result
from smart_home_bridge.models import DetectionFrame


class chicken_thread_detector_controller(device_controller):
    def __init__(
        self,
        detector: chicken_thread_detector,
        danger_scorer: DangerScorer | None = None,
        publishable: Publishable | None = None,
    ):
        self.detector = detector
        self.danger_scorer = danger_scorer or DangerScorer()
        self.publishable = publishable

    def set_publishable(self, publishable: Publishable | None):
        self.publishable = publishable

    def get_command(self, command: str) -> command:
        match command:
            case "get_detector_state":
                return get_detector_state_command(self.detector, self.publishable)
            case "reset_detector_state":
                return reset_detector_state_command(self.detector, self.publishable)
            case _:
                raise ValueError(f"Command {command} not found for device {self.detector.name}.")

    async def excecute_command(self, command: str) -> command_result:
        command_instance = self.get_command(command)
        return await command_instance.excecute()

    async def score_frame(self, frame: DetectionFrame) -> command_result:
        assessment = self.danger_scorer.score(frame.detections)
        self.detector.set_device_state(assessment)

        if self.publishable is not None:
            publish_result = self.publishable(assessment.to_json())
            if inspect.isawaitable(publish_result):
                await publish_result

        return command_result(data=assessment)

    async def score_frame_from_json(self, payload: str) -> command_result:
        return await self.score_frame(DetectionFrame.from_json(payload))


class detector_command(command):
    def __init__(
        self,
        detector: chicken_thread_detector,
        publishable: Publishable | None = None,
    ):
        super().__init__(publishable)
        self.detector = detector


class get_detector_state_command(detector_command):
    async def excecute(self):
        state = self.detector.get_device_state()
        await self.publish(state.to_json())
        return command_result(data=state)


class reset_detector_state_command(detector_command):
    async def excecute(self):
        from smart_home_bridge.models import DangerAssessment, ThreatLevel
        state = DangerAssessment(level=ThreatLevel.NONE, score=0.0)
        self.detector.set_device_state(state)
        await self.publish(state.to_json())
        return command_result(data=state)
