from dataclasses import dataclass, field

from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.config import app_config
from smart_home_contracts.chicken_thread import DangerAssessment


@dataclass(frozen=True)
class GuiBridgeSnapshot:
    door_state: str
    threat_assessment: DangerAssessment
    command_topic: str
    detector_topic: str
    http_endpoint: str
    camera_endpoint: str
    camera_health: str = "Unknown"
    backend_status: str = "Ready"
    last_activity_entries: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GuiBridgeViewModel:
    door_state: str
    door_tone: str
    threat_level: str
    threat_score: float
    threat_count: int
    threat_tone: str
    command_topic: str
    detector_topic: str
    http_endpoint: str
    camera_endpoint: str
    camera_health: str
    camera_health_tone: str
    backend_status: str
    backend_status_tone: str
    last_activity_entries: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_snapshot(cls, snapshot: GuiBridgeSnapshot):
        threat_level = snapshot.threat_assessment.level.value
        return cls(
            door_state=snapshot.door_state,
            door_tone=door_tone(snapshot.door_state),
            threat_level=threat_level,
            threat_score=snapshot.threat_assessment.score,
            threat_count=snapshot.threat_assessment.detection_count,
            threat_tone=threat_tone(threat_level),
            command_topic=snapshot.command_topic,
            detector_topic=snapshot.detector_topic,
            http_endpoint=snapshot.http_endpoint,
            camera_endpoint=snapshot.camera_endpoint,
            camera_health=snapshot.camera_health,
            camera_health_tone=camera_health_tone(snapshot.camera_health),
            backend_status=snapshot.backend_status,
            backend_status_tone=backend_status_tone(snapshot.backend_status),
            last_activity_entries=snapshot.last_activity_entries,
        )


def snapshot_from_config(
    config: app_config,
    door_state: str,
    threat_assessment: DangerAssessment,
    command_topic: str,
    detector_topic: str,
    camera_health: str = "Unknown",
    backend_status: str = "Ready",
    last_activity_entries: tuple[str, ...] = (),
) -> GuiBridgeSnapshot:
    return GuiBridgeSnapshot(
        door_state=door_state,
        threat_assessment=threat_assessment,
        command_topic=command_topic,
        detector_topic=detector_topic,
        http_endpoint=f"{config.http.host}:{config.http.port}",
        camera_endpoint=(
            f"{config.camera.host}:{config.camera.port}{config.camera.jpg_endpoint}"
        ),
        camera_health=camera_health,
        backend_status=backend_status,
        last_activity_entries=last_activity_entries,
    )


def door_tone(value: str) -> str:
    if value == door_position.OPEN.value:
        return "warning"
    if value == door_position.CLOSED.value:
        return "good"
    return "neutral"


def threat_tone(value: str) -> str:
    if value in {"critical", "high"}:
        return "danger"
    if value == "medium":
        return "warning"
    if value == "low":
        return "notice"
    return "good"


def camera_health_tone(value: str) -> str:
    if value == "Available":
        return "good"
    if value == "Unavailable":
        return "danger"
    return "neutral"


def backend_status_tone(value: str) -> str:
    if value in {"Ready", "Settings saved - restart backend required"}:
        return "good"
    if "failed" in value.lower() or "unavailable" in value.lower():
        return "danger"
    if (
        "saving" in value.lower()
        or "running" in value.lower()
        or "checking" in value.lower()
    ):
        return "working"
    return "neutral"
