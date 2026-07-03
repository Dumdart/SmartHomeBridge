from __future__ import annotations

from collections.abc import Callable

from smart_home_bridge.bridge_devices.chicken_door import (
    DoorGateway,
    DoorMqttPublisher,
    DoorMqttTopics,
    chicken_door,
    chicken_door_mqtt_callbacks,
    door_controller,
    door_position,
)
from smart_home_bridge.bridge_devices.runtime import (
    BridgeDeviceComposition,
    BridgeDeviceMqttBinding,
    BridgeDeviceRuntime,
    MqttClientFactory,
    build_topic,
)
from smart_home_bridge.config import DoorApiConfig, app_config
from smart_home_bridge.infrastructure.mqtt.mqtt_gate import MqttGate
from smart_home_bridge.infrastructure.omlet import OmletDoorClient
from smart_home_bridge.services.mqtt_usage_reporter import MqttUsageReporter

CHICKEN_DOOR_COMMAND_TOPIC = "chicken-door/command"


def create_chicken_door_composition(
    config: app_config,
    door_gateway_factory: Callable[[DoorApiConfig], DoorGateway | None] = OmletDoorClient,
) -> BridgeDeviceComposition:
    device_config = config.devices.for_device("chicken_door")
    command_topic = device_config.topic("command", CHICKEN_DOOR_COMMAND_TOPIC)
    door = chicken_door(
        device_config.device_id or 1,
        device_config.name or "door",
        door_position.UNKNOWN,
    )
    gateway = door_gateway_factory(config.door_api)
    controller = door_controller(door, gateway=gateway)
    topics = build_door_mqtt_topics(config.mqtt.base_topic, device_config)

    def create_runtime(mqtt_client_factory: MqttClientFactory) -> BridgeDeviceRuntime:
        client = mqtt_client_factory(config.mqtt)
        gate = MqttGate(
            config.mqtt,
            chicken_door_mqtt_callbacks(controller),
            command_topic,
            client=client,
        )
        publisher = DoorMqttPublisher(topics, client.publish)
        usage_reporter = MqttUsageReporter(client.publish, config.mqtt.base_topic)

        controller.set_publishable(publisher.publish_status)
        controller.set_usage_reporter(
            lambda command, success, position: usage_reporter.report_chicken_door(
                command,
                success,
                position.value if position is not None else None,
            )
        )

        return BridgeDeviceRuntime(
            name=device_config.name or "chicken_door",
            mqtt_config=config.mqtt,
            mqtt_bindings=(
                BridgeDeviceMqttBinding(
                    name="commands",
                    topic=command_topic,
                    gate=gate,
                    ignore_retained=True,
                    publish_topics=(
                        topics.status,
                        topics.status_code,
                        topics.fault,
                        topics.connected,
                        topics.battery,
                        topics.light_level,
                    ),
                ),
            ),
            handles={
                "chicken_door_mqtt_gate": gate,
                "door_mqtt_publisher": publisher,
                "door_usage_reporter": usage_reporter,
            },
        )

    return BridgeDeviceComposition(
        key="chicken_door",
        config=device_config,
        handles={
            "door": door,
            "door_controller": controller,
            "door_topics": topics,
            "command_topic": build_topic(config.mqtt.base_topic, command_topic),
        },
        create_runtime=create_runtime,
    )


def build_door_mqtt_topics(
    base_topic: str,
    device_config=None,
) -> DoorMqttTopics:
    def topic(name: str, default: str) -> str:
        if device_config is None:
            return default
        return device_config.topic(name, default)

    return DoorMqttTopics(
        command=build_topic(base_topic, topic("command", CHICKEN_DOOR_COMMAND_TOPIC)),
        status=build_topic(base_topic, topic("status", "chicken-door/status")),
        status_code=build_topic(
            base_topic,
            topic("status_code", "chicken-door/status_code"),
        ),
        fault=build_topic(base_topic, topic("fault", "chicken-door/fault")),
        connected=build_topic(base_topic, topic("connected", "chicken-door/connected")),
        battery=build_topic(base_topic, topic("battery", "chicken-door/battery")),
        light_level=build_topic(
            base_topic,
            topic("light_level", "chicken-door/light_level"),
        ),
    )
