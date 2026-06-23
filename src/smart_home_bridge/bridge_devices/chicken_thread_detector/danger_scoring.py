from smart_home_bridge.bridge_devices.chicken_thread_detector.model_config import default_model_config
from smart_home_bridge.models import ChickenThreadModelConfig, DangerAssessment, Detection, ThreatLevel


class DangerScorer:
    def __init__(self, config: ChickenThreadModelConfig | None = None):
        self.config = config or default_model_config()

    def score(self, detections: tuple[Detection, ...] | list[Detection]) -> DangerAssessment:
        considered_detections = tuple(
            detection
            for detection in detections
            if detection.confidence >= self.config.confidence_threshold
        )
        scored_detections = tuple(
            detection
            for detection in considered_detections
            if self._detection_score(detection) > 0
        )
        score = max((self._detection_score(detection) for detection in scored_detections), default=0.0)

        return DangerAssessment(
            level=self._level_for_score(score),
            score=round(score, 4),
            triggering_detections=scored_detections,
            detection_count=len(considered_detections),
        )

    def _detection_score(self, detection: Detection) -> float:
        label = self.config.normalized_label(detection.label)
        risk = self.config.risk_by_label.get(label, 0.0)
        return risk * detection.confidence

    def _level_for_score(self, score: float) -> ThreatLevel:
        if score >= self.config.critical_threshold:
            return ThreatLevel.CRITICAL
        if score >= self.config.high_threshold:
            return ThreatLevel.HIGH
        if score >= self.config.medium_threshold:
            return ThreatLevel.MEDIUM
        if score > 0:
            return ThreatLevel.LOW
        return ThreatLevel.NONE
