from smart_home_bridge.core.device import device
from smart_home_bridge.models import DangerAssessment, ThreatLevel


class chicken_thread_detector(device):
    def __init__(self, device_id, name, assessment: DangerAssessment | None = None):
        self.device_id = device_id
        self.name = name
        self.assessment = assessment or DangerAssessment(
            level=ThreatLevel.NONE,
            score=0.0,
        )

    def get_device_state(self):
        return self.assessment

    def set_device_state(self, state):
        self.assessment = state
