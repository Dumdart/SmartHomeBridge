from types import SimpleNamespace

from smart_home_bridge.bridge_devices.chicken_door import door_position
from smart_home_bridge.config import DoorApiConfig
from smart_home_bridge.infrastructure.omlet.omlet_door_client import (
    OmletDoorClient,
    SmartCoopHttpClient,
)


def test_omlet_door_client_maps_device_state_to_bridge_status():
    client = _client_with(FakeOmlet(_device("openpending")))

    status = client.get_state()

    assert status.position == door_position.OPEN_PENDING
    assert status.fault == "none"
    assert status.light_level == 123
    assert status.battery_level == 87
    assert status.power_source == "battery"
    assert status.wifi_strength == 72
    assert status.connected is True
    assert status.last_open_time == "2026-07-03T06:00:00Z"
    assert status.last_close_time == "2026-07-02T21:00:00Z"


def test_omlet_door_client_opens_by_action_name_and_refetches_state():
    omlet = FakeOmlet(
        _device("closed", actions=[SimpleNamespace(name="open", pending="openpending")]),
        refreshed_device=_device("openpending"),
    )
    client = _client_with(omlet)

    status = client.open()

    assert status.position == door_position.OPEN_PENDING
    assert omlet.performed_actions == ["open"]
    assert omlet.requested_device_ids == ["device-id", "device-id"]


def test_omlet_door_client_supports_sdk_action_name_field():
    omlet = FakeOmlet(
        _device("open", actions=[SimpleNamespace(actionName="close", pending="closepending")]),
        refreshed_device=_device("closepending"),
    )
    client = _client_with(omlet)

    status = client.close()

    assert status.position == door_position.CLOSE_PENDING
    assert omlet.performed_actions == ["close"]


def test_omlet_door_client_returns_pending_when_refresh_after_action_fails():
    omlet = FakeOmlet(
        _device("open", actions=[SimpleNamespace(name="stop", pending="stopping")]),
        refresh_error=RuntimeError("offline after action"),
    )
    client = _client_with(omlet)

    status = client.stop()

    assert status.position == door_position.STOPPING
    assert omlet.performed_actions == ["stop"]


def test_omlet_door_client_raises_when_action_is_missing():
    omlet = FakeOmlet(_device("closed", actions=[]))
    client = _client_with(omlet)

    try:
        client.open()
    except ValueError as exc:
        assert str(exc) == "Action open not found for Omlet device."
    else:
        raise AssertionError("Expected missing Omlet action to be rejected")


def test_smartcoop_http_client_applies_timeout_to_every_request():
    session = FakeSession()
    client = SmartCoopHttpClient("api-key", 7.5, session=session)

    assert client.get("device/device-id", params={"details": "all"}) == {
        "ok": True,
    }
    assert client.post("action/open", json={"value": True}) == {"ok": True}

    assert session.requests == [
        (
            "GET",
            "https://x107.omlet.co.uk/api/v1/device/device-id",
            7.5,
            {"params": {"details": "all"}},
        ),
        (
            "POST",
            "https://x107.omlet.co.uk/api/v1/action/open",
            7.5,
            {"json": {"value": True}},
        ),
    ]


class FakeSession:
    def __init__(self):
        self.requests = []

    def request(self, method, url, headers, timeout, **kwargs):
        assert headers["Authorization"] == "Bearer api-key"
        self.requests.append((method, url, timeout, kwargs))
        return FakeResponse()


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class FakeOmlet:
    def __init__(self, device, refreshed_device=None, refresh_error=None):
        self.device = device
        self.refreshed_device = refreshed_device or device
        self.refresh_error = refresh_error
        self.get_count = 0
        self.performed_actions = []
        self.requested_device_ids = []

    def get_device_by_id(self, device_id):
        self.requested_device_ids.append(device_id)
        self.get_count += 1
        if self.get_count > 1 and self.refresh_error is not None:
            raise self.refresh_error
        if self.get_count > 1:
            return self.refreshed_device
        return self.device

    def perform_action(self, action):
        self.performed_actions.append(
            getattr(action, "actionName", None) or getattr(action, "name", None),
        )


def _client_with(omlet):
    return OmletDoorClient(
        DoorApiConfig(api_key="api-key", device_id="device-id"),
        client_factory=lambda api_key: SimpleNamespace(api_key=api_key),
        omlet_factory=lambda client: omlet,
    )


def _device(position, actions=None):
    return SimpleNamespace(
        state=SimpleNamespace(
            door=SimpleNamespace(
                state=position,
                fault="none",
                lightLevel=123,
                lastOpenTime="2026-07-03T06:00:00Z",
                lastCloseTime="2026-07-02T21:00:00Z",
            ),
            general=SimpleNamespace(
                batteryLevel=87,
                powerSource="battery",
            ),
            connectivity=SimpleNamespace(
                wifiStrength="72",
                connected=True,
            ),
        ),
        actions=actions if actions is not None else [],
    )
