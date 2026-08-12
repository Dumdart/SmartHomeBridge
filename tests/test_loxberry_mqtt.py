from pathlib import Path

from smart_home_bridge.loxberry_mqtt import (
    build_mqtt_subscriptions,
    sync_mqtt_subscriptions,
)


def test_builds_subscriptions_from_every_configured_topic():
    subscriptions = build_mqtt_subscriptions(
        {
            "MQTT_BASE_TOPIC": "SmartHome/Huehnerstall/",
            "CHICKEN_DOOR_COMMAND_TOPIC": "/door/command",
            "CHICKEN_DOOR_STATUS_TOPIC": "door/status",
            "CHICKEN_DOOR_USAGE_TOPIC": "usage/door",
            "LOG_LEVEL": "INFO",
        }
    )

    assert subscriptions == (
        "SmartHome/Huehnerstall/door/command",
        "SmartHome/Huehnerstall/door/status",
        "SmartHome/Huehnerstall/usage/door",
    )


def test_sync_replaces_legacy_subscriptions_with_current_settings(tmp_path: Path):
    config_path = tmp_path / "smart-home-bridge.ini"
    subscriptions_path = tmp_path / "mqtt_subscriptions.cfg"
    config_path.write_text(
        "\n".join(
            (
                "[smart-home-bridge]",
                "MQTT_BASE_TOPIC=SmartHome/Huehnerstall",
                "CHICKEN_DOOR_COMMAND_TOPIC=door/command",
                "CHICKEN_DOOR_USAGE_TOPIC=usage/door",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    subscriptions_path.write_text(
        "smart-home-bridge/chicken-door\n",
        encoding="utf-8",
    )

    sync_mqtt_subscriptions(config_path, subscriptions_path)

    assert subscriptions_path.read_text(encoding="utf-8").splitlines() == [
        "SmartHome/Huehnerstall/door/command",
        "SmartHome/Huehnerstall/usage/door",
    ]
