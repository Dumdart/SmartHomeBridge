from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from smart_home_bridge.bridge_devices.registry import create_bridge_device_compositions
from smart_home_bridge.bridge_devices.runtime import BridgeDeviceComposition
from smart_home_bridge.config import app_config
from smart_home_bridge.infrastructure.api.http_gate import HttpGate


@dataclass(frozen=True)
class BridgeComposition:
    config: app_config
    http_gate: HttpGate
    device_compositions: tuple[BridgeDeviceComposition, ...]
    handles: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.handles[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def create_bridge_composition(
    config: app_config,
    device_composition_factory: Callable[
        [app_config],
        tuple[BridgeDeviceComposition, ...],
    ] = create_bridge_device_compositions,
) -> BridgeComposition:
    device_compositions = device_composition_factory(config)
    handles: dict[str, Any] = {}
    for device_composition in device_compositions:
        handles.update(device_composition.handles)

    return BridgeComposition(
        config=config,
        http_gate=HttpGate(config.http),
        device_compositions=device_compositions,
        handles=handles,
    )
