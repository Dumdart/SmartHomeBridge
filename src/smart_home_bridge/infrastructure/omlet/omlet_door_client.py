import logging
from collections.abc import Callable
from typing import Any

import requests

from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.bridge_devices.chicken_door.door_status import door_status
from smart_home_bridge.config import DoorApiConfig

logger = logging.getLogger(__name__)


class SmartCoopHttpClient:
    base_url = "https://x107.omlet.co.uk/api/v1"

    def __init__(
        self,
        client_secret: str,
        timeout_seconds: float,
        session: requests.Session | None = None,
    ):
        self.client_secret = client_secret
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def get(self, endpoint: str, params=None):
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, json=None):
        return self._request("POST", endpoint, json=json)

    def patch(self, endpoint: str, json=None):
        return self._request("PATCH", endpoint, json=json)

    def delete(self, endpoint: str, json=None):
        return self._request("DELETE", endpoint, json=json)

    def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.request(
            method,
            url,
            headers={
                "Authorization": f"Bearer {self.client_secret}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout_seconds,
            **kwargs,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.error(
                "%s %s failed with status %s",
                method,
                url,
                response.status_code,
            )
            raise
        if response.status_code == 204:
            return None
        return response.json()


class OmletDoorClient:
    def __init__(
        self,
        config: DoorApiConfig,
        client_factory: Callable[[str], Any] | None = None,
        omlet_factory: Callable[[Any], Any] | None = None,
    ):
        self.config = config
        if omlet_factory is None:
            from smartcoop.api.omlet import Omlet

            omlet_factory = Omlet
        if client_factory is None:
            client_factory = lambda api_key: SmartCoopHttpClient(
                api_key,
                config.request_timeout_seconds,
            )

        self._omlet = omlet_factory(client_factory(config.api_key))

    def get_state(self) -> door_status:
        return self._status_from_device(self._get_device())

    def open(self) -> door_status:
        return self._perform_action("open")

    def close(self) -> door_status:
        return self._perform_action("close")

    def stop(self) -> door_status:
        return self._perform_action("stop")

    def _get_device(self):
        return self._omlet.get_device_by_id(self.config.device_id)

    def _perform_action(self, action_name: str) -> door_status:
        device = self._get_device()
        action = _find_action(device, action_name)
        self._omlet.perform_action(action)

        try:
            return self.get_state()
        except Exception:
            pending = getattr(action, "pending", None)
            if pending:
                logger.warning(
                    "Omlet door action %s succeeded, but state refresh failed.",
                    action_name,
                    exc_info=True,
                )
                return door_status(position=_map_position(pending))
            raise

    def _status_from_device(self, device) -> door_status:
        state = getattr(device, "state", None)
        door_state = getattr(state, "door", None)
        general = getattr(state, "general", None)
        connectivity = getattr(state, "connectivity", None)

        return door_status(
            position=_map_position(getattr(door_state, "state", None)),
            fault=getattr(door_state, "fault", None),
            light_level=_int_or_none(getattr(door_state, "lightLevel", None)),
            battery_level=_int_or_none(getattr(general, "batteryLevel", None)),
            power_source=getattr(general, "powerSource", None),
            wifi_strength=_int_or_none(getattr(connectivity, "wifiStrength", None)),
            connected=getattr(connectivity, "connected", None),
            last_open_time=getattr(door_state, "lastOpenTime", None),
            last_close_time=getattr(door_state, "lastCloseTime", None),
        )


def _find_action(device, action_name: str):
    for action in getattr(device, "actions", ()):
        sdk_action_name = getattr(action, "actionName", None) or getattr(action, "name", None)
        if sdk_action_name == action_name:
            return action

    raise ValueError(f"Action {action_name} not found for Omlet device.")


def _map_position(value: object) -> door_position:
    if value is None:
        return door_position.UNKNOWN

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )
    positions = {
        "open": door_position.OPEN,
        "closed": door_position.CLOSED,
        "opening": door_position.OPENING,
        "closing": door_position.CLOSING,
        "openpending": door_position.OPEN_PENDING,
        "closepending": door_position.CLOSE_PENDING,
        "stopping": door_position.STOPPING,
        "unknown": door_position.UNKNOWN,
    }
    return positions.get(normalized, door_position.UNKNOWN)


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        digits = "".join(character for character in str(value) if character.isdigit())
        if digits == "":
            return None
        return int(digits)
