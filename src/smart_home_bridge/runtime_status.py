from __future__ import annotations

from typing import Any

from smart_home_bridge.bridge_devices.runtime import BridgeDeviceRuntime, build_topic
from smart_home_bridge.config import app_config


def build_backend_status(
    config: app_config,
    device_runtimes: tuple[BridgeDeviceRuntime, ...],
) -> dict[str, Any]:
    return {
        "mqtt": {
            "host": config.mqtt.host,
            "port": config.mqtt.port,
            "base_topic": config.mqtt.base_topic,
            "use_tls": config.mqtt.use_tls,
            "username_configured": config.mqtt.username != "",
            "password_configured": config.mqtt.password != "",
        },
        "http": {
            "host": config.http.host,
            "port": config.http.port,
        },
        "log_level": config.log_level,
        "log_file_path": config.log_file_path,
        "camera": {
            "host": config.camera.host,
            "port": config.camera.port,
            "jpg_endpoint": config.camera.jpg_endpoint,
            "health_endpoint": config.camera.health_endpoint,
            "timeout_seconds": config.camera.timeout_seconds,
            "max_jpeg_bytes": config.camera.max_jpeg_bytes,
            "auth_token_configured": config.camera.auth_token != "",
        },
        "chicken_threat": {
            "enabled": config.chicken_threat.enabled,
            "inference_url": config.chicken_threat.inference_url,
            "inference_timeout_seconds": (
                config.chicken_threat.inference_timeout_seconds
            ),
            "poll_interval_seconds": config.chicken_threat.poll_interval_seconds,
            "pipeline_running": _pipeline_running(device_runtimes),
        },
        "devices": {
            "enabled": config.devices.enabled,
            "runtimes": [_runtime_status(config, runtime) for runtime in device_runtimes],
        },
    }


def _runtime_status(config: app_config, runtime: BridgeDeviceRuntime) -> dict[str, Any]:
    return {
        "name": runtime.name,
        "running": runtime.is_running,
        "mqtt_running": runtime.mqtt_running,
        "background_services_running": runtime.background_services_running,
        "mqtt_bindings": [
            {
                "name": binding.name,
                "topic": build_topic(config.mqtt.base_topic, binding.topic),
                "ignore_retained": binding.ignore_retained,
                "publish_topics": binding.publish_topics,
            }
            for binding in runtime.mqtt_bindings
        ],
    }


def _pipeline_running(device_runtimes: tuple[BridgeDeviceRuntime, ...]) -> bool:
    for runtime in device_runtimes:
        for service in runtime.background_services:
            is_running = getattr(service, "is_running", None)
            if isinstance(is_running, bool) and is_running:
                return True
    return False
