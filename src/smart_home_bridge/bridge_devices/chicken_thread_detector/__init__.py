"""Chicken thread detector bridge device."""

from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector import (
    chicken_thread_detector,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_controller import (
    chicken_thread_detector_controller,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.chicken_thread_detector_mqtt_callbacks import (
    chicken_thread_detector_mqtt_callbacks,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.danger_scoring import DangerScorer
from smart_home_bridge.bridge_devices.chicken_thread_detector.detector import LocalChickenThreadDetector
from smart_home_bridge.bridge_devices.chicken_thread_detector.inference import (
    ChickenThreatInferenceService,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.model_config import default_model_config
from smart_home_bridge.bridge_devices.chicken_thread_detector.pipeline import (
    ChickenThreatDetectionPipeline,
)
from smart_home_bridge.bridge_devices.chicken_thread_detector.scan import (
    ChickenThreatScanResult,
    ChickenThreatScanService,
)

__all__ = [
    "ChickenThreatDetectionPipeline",
    "ChickenThreatInferenceService",
    "ChickenThreatScanResult",
    "ChickenThreatScanService",
    "DangerScorer",
    "LocalChickenThreadDetector",
    "chicken_thread_detector",
    "chicken_thread_detector_controller",
    "chicken_thread_detector_mqtt_callbacks",
    "default_model_config",
]
