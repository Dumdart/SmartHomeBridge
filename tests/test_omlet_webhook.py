import asyncio

import httpx

from smart_home_bridge.bridge_devices.chicken_door import omlet_webhook
from smart_home_bridge.bridge_devices.chicken_door import (
    MAX_WEBHOOK_BODY_BYTES,
    OMLET_WEBHOOK_PATH,
    DoorMqttPublisher,
    DoorMqttTopics,
    OmletDoorWebhookHandler,
    OmletWebhookServer,
    chicken_door,
    create_omlet_webhook_app,
    door_position,
)
from smart_home_bridge.config import DoorApiConfig, HttpConfig, OmletWebhookConfig

TOKEN = "0123456789abcdef0123456789abcdef"


def test_webhook_authorization_uses_constant_time_comparison(monkeypatch):
    compared = []

    def compare(supplied, expected):
        compared.append((supplied, expected))
        return supplied == expected

    monkeypatch.setattr(omlet_webhook.secrets, "compare_digest", compare)

    assert omlet_webhook._authorized(f"Bearer {TOKEN}", TOKEN) is True
    assert compared == [(TOKEN, TOKEN)]


def test_webhook_accepts_bearer_token_and_publishes_only_position_topics():
    async def scenario():
        door, published, app = _webhook_app()
        response = await _post(
            app,
            _payload("Door State", "opening"),
            authorization=f"Bearer {TOKEN}",
        )

        assert response.status_code == 200
        assert response.json() == {
            "accepted": True,
            "processed": True,
            "state": "opening",
        }
        assert door.position == door_position.OPENING
        assert published == [
            ("base/chicken-door/status", "opening", True),
            ("base/chicken-door/status_code", "3", True),
        ]

    asyncio.run(scenario())


def test_webhook_accepts_raw_authorization_and_documented_parameter_name():
    async def scenario():
        door, published, app = _webhook_app()
        response = await _post(
            app,
            _payload("Door Open State", "closed"),
            authorization=TOKEN,
        )

        assert response.status_code == 200
        assert door.position == door_position.CLOSED
        assert published[-1] == ("base/chicken-door/status_code", "2", True)

    asyncio.run(scenario())


def test_webhook_rejects_invalid_auth_before_reading_oversized_body():
    async def scenario():
        _door, published, app = _webhook_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                OMLET_WEBHOOK_PATH,
                content=b"x" * (MAX_WEBHOOK_BODY_BYTES + 1),
                headers={"Content-Type": "application/json"},
            )

        assert response.status_code == 401
        assert published == []

    asyncio.run(scenario())


def test_webhook_validates_content_type_size_payload_and_device():
    async def scenario():
        _door, published, app = _webhook_app()
        headers = {"Authorization": f"Bearer {TOKEN}"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            wrong_type = await client.post(
                OMLET_WEBHOOK_PATH,
                content="text",
                headers={**headers, "Content-Type": "text/plain"},
            )
            oversized = await client.post(
                OMLET_WEBHOOK_PATH,
                content=b"{" + b" " * MAX_WEBHOOK_BODY_BYTES + b"}",
                headers={**headers, "Content-Type": "application/json"},
            )
            malformed = await client.post(
                OMLET_WEBHOOK_PATH,
                content="{",
                headers={**headers, "Content-Type": "application/json"},
            )
            mismatch = await client.post(
                OMLET_WEBHOOK_PATH,
                json={**_payload("Door State", "open"), "deviceId": "other"},
                headers=headers,
            )

        assert wrong_type.status_code == 415
        assert oversized.status_code == 413
        assert malformed.status_code == 400
        assert mismatch.status_code == 403
        assert published == []

    asyncio.run(scenario())


def test_webhook_accepts_verification_and_ignores_other_parameters():
    async def scenario():
        _door, published, app = _webhook_app()
        verification = await _post(app, {}, authorization=f"Bearer {TOKEN}")
        ignored = await _post(
            app,
            _payload("Power Source", "battery"),
            authorization=f"Bearer {TOKEN}",
        )

        assert verification.status_code == 200
        assert verification.json()["processed"] is False
        assert ignored.status_code == 200
        assert ignored.json()["processed"] is False
        assert published == []

    asyncio.run(scenario())


def test_webhook_maps_all_supported_door_states():
    expected = {
        "open": (door_position.OPEN, "1"),
        "closed": (door_position.CLOSED, "2"),
        "opening": (door_position.OPENING, "3"),
        "closing": (door_position.CLOSING, "4"),
        "openpending": (door_position.OPEN_PENDING, "3"),
        "close-pending": (door_position.CLOSE_PENDING, "4"),
        "stopping": (door_position.STOPPING, "5"),
        "calibrating": (door_position.CALIBRATING, "0"),
        "open stopped": (door_position.OPEN_STOPPED, "5"),
        "closestopped": (door_position.CLOSE_STOPPED, "5"),
        "unknown": (door_position.UNKNOWN, "0"),
    }

    async def scenario():
        for value, (position, code) in expected.items():
            door, published, app = _webhook_app()
            response = await _post(
                app,
                _payload("Door State", value),
                authorization=f"Bearer {TOKEN}",
            )
            assert response.status_code == 200
            assert door.position == position
            assert published[-1][1] == code

    asyncio.run(scenario())


def test_webhook_returns_503_when_mqtt_publication_fails():
    async def scenario():
        async def fail(*_args, **_kwargs):
            raise RuntimeError("mqtt unavailable")

        door = chicken_door(1, "door", door_position.CLOSED)
        publisher = DoorMqttPublisher(_topics(), fail)
        handler = OmletDoorWebhookHandler(_door_api(), door, publisher)
        app = create_omlet_webhook_app(_webhook_config(), handler)

        response = await _post(
            app,
            _payload("Door State", "open"),
            authorization=f"Bearer {TOKEN}",
        )

        assert response.status_code == 503

    asyncio.run(scenario())


def test_webhook_serializes_concurrent_state_publications():
    async def scenario():
        active = 0
        max_active = 0

        async def publish(*_args, **_kwargs):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0)
            active -= 1

        door = chicken_door(1, "door", door_position.UNKNOWN)
        handler = OmletDoorWebhookHandler(
            _door_api(),
            door,
            DoorMqttPublisher(_topics(), publish),
        )

        await asyncio.gather(
            handler.process(_payload("Door State", "opening")),
            handler.process(_payload("Door State", "open")),
        )

        assert max_active == 1
        assert door.position == door_position.OPEN

    asyncio.run(scenario())


def test_webhook_server_start_and_stop_lifecycle(monkeypatch):
    events = []

    class FakeServer:
        def __init__(self, _configuration):
            self.started = False
            self.should_exit = False

        async def serve(self):
            events.append("start")
            self.started = True
            while not self.should_exit:
                await asyncio.sleep(0)
            events.append("stop")

    monkeypatch.setattr(
        "smart_home_bridge.bridge_devices.chicken_door.omlet_webhook.uvicorn.Server",
        FakeServer,
    )
    async def publish(*_args, **_kwargs):
        pass

    door = chicken_door(1, "door", door_position.UNKNOWN)
    handler = OmletDoorWebhookHandler(
        _door_api(),
        door,
        DoorMqttPublisher(_topics(), publish),
    )

    async def scenario():
        server = OmletWebhookServer(
            HttpConfig("127.0.0.1", 8080),
            _webhook_config(),
            handler,
        )
        await server.start()
        assert server.is_running is True
        await server.stop()
        assert server.is_running is False

    asyncio.run(scenario())
    assert events == ["start", "stop"]


def test_webhook_server_converts_uvicorn_bind_exit_to_runtime_error(monkeypatch):
    class FailingServer:
        def __init__(self, _configuration):
            self.started = False
            self.should_exit = False

        async def serve(self):
            raise SystemExit(3)

    monkeypatch.setattr(
        "smart_home_bridge.bridge_devices.chicken_door.omlet_webhook.uvicorn.Server",
        FailingServer,
    )

    async def publish(*_args, **_kwargs):
        pass

    handler = OmletDoorWebhookHandler(
        _door_api(),
        chicken_door(1, "door", door_position.UNKNOWN),
        DoorMqttPublisher(_topics(), publish),
    )

    async def scenario():
        server = OmletWebhookServer(
            HttpConfig("0.0.0.0", 8080),
            _webhook_config(),
            handler,
        )
        try:
            await server.start()
        except RuntimeError as exc:
            assert "0.0.0.0:8080" in str(exc)
            assert "already be in use" in str(exc)
        else:
            raise AssertionError("Expected a bind startup failure")

        assert server.is_running is False
        await server.stop()

    asyncio.run(scenario())


def _webhook_app():
    published = []

    async def publish(topic, payload, retain=False):
        published.append((topic, payload, retain))

    door = chicken_door(1, "door", door_position.UNKNOWN)
    publisher = DoorMqttPublisher(_topics(), publish)
    handler = OmletDoorWebhookHandler(_door_api(), door, publisher)
    return door, published, create_omlet_webhook_app(_webhook_config(), handler)


async def _post(app, payload, authorization):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            OMLET_WEBHOOK_PATH,
            json=payload,
            headers={"Authorization": authorization},
        )


def _payload(parameter, new_value):
    return {
        "deviceId": "device-id",
        "parameterName": parameter,
        "oldValue": "closed",
        "newValue": new_value,
    }


def _door_api():
    return DoorApiConfig(api_key="api-key", device_id="device-id")


def _webhook_config():
    return OmletWebhookConfig(enabled=True, token=TOKEN)


def _topics():
    return DoorMqttTopics(
        command="base/chicken-door/command",
        status="base/chicken-door/status",
        status_code="base/chicken-door/status_code",
        fault="base/chicken-door/fault",
        connected="base/chicken-door/connected",
        battery="base/chicken-door/battery",
        light_level="base/chicken-door/light_level",
    )
