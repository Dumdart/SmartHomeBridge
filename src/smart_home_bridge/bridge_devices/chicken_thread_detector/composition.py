from __future__ import annotations

from smart_home_bridge.bridge_devices.chicken_thread_detector import (
    ChickenThreatDetectionPipeline,
    ChickenThreatInferenceClient,
    DangerScorer,
    chicken_thread_detector,
    chicken_thread_detector_controller,
    chicken_thread_detector_mqtt_callbacks,
    default_model_config,
)
from smart_home_bridge.bridge_devices.runtime import (
    BridgeDeviceComposition,
    BridgeDeviceMqttBinding,
    BridgeDeviceRuntime,
    MqttClientFactory,
    build_topic,
)
from smart_home_bridge.config import app_config
from smart_home_bridge.infrastructure.camera import CameraClient
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttGate
from smart_home_bridge.services.mqtt_usage_reporter import MqttUsageReporter

CHICKEN_THREAD_DETECTOR_TOPIC = "chicken-thread-detector"


def create_chicken_thread_detector_composition(
    config: app_config,
) -> BridgeDeviceComposition:
    device_config = config.devices.for_device("chicken_thread_detector")
    detection_topic = device_config.topic(
        "detections",
        CHICKEN_THREAD_DETECTOR_TOPIC,
    )
    model_config = default_model_config()
    detector = chicken_thread_detector(
        device_config.device_id or 2,
        device_config.name or "chicken_thread_detector",
    )
    controller = chicken_thread_detector_controller(
        detector,
        danger_scorer=DangerScorer(model_config),
    )
    camera_client = CameraClient(config.camera)
    inference_service = ChickenThreatInferenceClient(
        config.chicken_threat.inference_url,
        timeout_seconds=config.chicken_threat.inference_timeout_seconds,
    )

    def create_runtime(mqtt_client_factory: MqttClientFactory) -> BridgeDeviceRuntime:
        gate = MqttGate(
            config.mqtt,
            chicken_thread_detector_mqtt_callbacks(controller),
            detection_topic,
            client=mqtt_client_factory(config.mqtt),
        )
        controller.set_publishable(gate.publish)
        pipeline = create_chicken_threat_pipeline(
            config,
            camera_client,
            inference_service,
            controller,
        )
        usage_reporter = MqttUsageReporter(gate.client.publish, config.mqtt.base_topic)
        if pipeline is not None:
            pipeline.usage_reporter = usage_reporter.report_camera_inference

        return BridgeDeviceRuntime(
            name=device_config.name or "chicken_thread_detector",
            mqtt_config=config.mqtt,
            mqtt_bindings=(
                BridgeDeviceMqttBinding(
                    name="detections",
                    topic=detection_topic,
                    gate=gate,
                    ignore_retained=True,
                    publish_topics=(build_topic(config.mqtt.base_topic, detection_topic),),
                ),
            ),
            background_services=() if pipeline is None else (pipeline,),
            handles={
                "chicken_thread_detector_mqtt_gate": gate,
                "chicken_threat_pipeline": pipeline,
                "camera_inference_usage_reporter": usage_reporter,
            },
        )

    return BridgeDeviceComposition(
        key="chicken_thread_detector",
        config=device_config,
        handles={
            "threat_detector": detector,
            "thread_detector": detector,
            "threat_model_config": model_config,
            "thread_model_config": model_config,
            "threat_detector_controller": controller,
            "thread_detector_controller": controller,
            "camera_client": camera_client,
            "threat_inference_service": inference_service,
            "detector_topic": build_topic(config.mqtt.base_topic, detection_topic),
        },
        create_runtime=create_runtime,
    )


def create_chicken_threat_pipeline(
    config: app_config,
    camera_client: CameraClient,
    inference_service: ChickenThreatInferenceClient,
    controller: chicken_thread_detector_controller,
) -> ChickenThreatDetectionPipeline | None:
    if not config.chicken_threat.enabled:
        return None

    return ChickenThreatDetectionPipeline(
        camera_client=camera_client,
        inference_service=inference_service,
        detector_controller=controller,
        poll_interval_seconds=config.chicken_threat.poll_interval_seconds,
        source=config.camera.host,
    )
