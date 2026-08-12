from __future__ import annotations

import sys
from collections.abc import Mapping
from configparser import ConfigParser
from pathlib import Path


def build_mqtt_subscriptions(settings: Mapping[str, str]) -> tuple[str, ...]:
    base_topic = settings.get("MQTT_BASE_TOPIC", "").strip().strip("/")
    if base_topic == "":
        raise ValueError("MQTT_BASE_TOPIC is required to build subscriptions")

    subscriptions: list[str] = []
    for name, value in settings.items():
        if name == "MQTT_BASE_TOPIC" or not name.endswith("_TOPIC"):
            continue
        device_topic = value.strip().strip("/")
        if device_topic == "":
            continue
        subscription = f"{base_topic}/{device_topic}"
        if subscription not in subscriptions:
            subscriptions.append(subscription)
    return tuple(subscriptions)


def sync_mqtt_subscriptions(
    config_path: str | Path,
    subscriptions_path: str | Path | None = None,
) -> Path:
    source = Path(config_path)
    destination = (
        Path(subscriptions_path)
        if subscriptions_path is not None
        else source.with_name("mqtt_subscriptions.cfg")
    )
    parser = ConfigParser()
    parser.optionxform = str
    if not parser.read(source, encoding="utf-8"):
        raise ValueError(f"Missing LoxBerry bridge config file: {source}")

    settings: dict[str, str] = {}
    for section in parser.sections():
        settings.update(
            (name.upper(), value.strip())
            for name, value in parser.items(section)
        )
    subscriptions = build_mqtt_subscriptions(settings)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(destination.suffix + ".tmp")
    temporary_path.write_text(
        "\n".join(subscriptions) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(destination)
    return destination


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: smart-home-bridge-sync-mqtt-subscriptions CONFIG_FILE"
        )
    destination = sync_mqtt_subscriptions(sys.argv[1])
    print(f"MQTT subscriptions synchronized: {destination}")

