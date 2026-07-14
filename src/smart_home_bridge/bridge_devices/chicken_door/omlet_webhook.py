from __future__ import annotations

import asyncio
import json
import logging
import secrets
from collections.abc import Mapping
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from smart_home_bridge.bridge_devices.chicken_door.chicken_door import (
    chicken_door,
    door_position,
    parse_door_position,
)
from smart_home_bridge.bridge_devices.chicken_door.door_mqtt_publisher import (
    DoorMqttPublisher,
)
from smart_home_bridge.config import DoorApiConfig, HttpConfig, OmletWebhookConfig

OMLET_WEBHOOK_PATH = "/webhooks/omlet/door-state"
MAX_WEBHOOK_BODY_BYTES = 16 * 1024
DOOR_STATE_PARAMETERS = {"doorstate", "dooropenstate"}

logger = logging.getLogger(__name__)


class InvalidWebhookPayload(ValueError):
    pass


class WebhookDeviceMismatch(PermissionError):
    pass


class WebhookBodyTooLarge(ValueError):
    pass


class OmletDoorWebhookHandler:
    def __init__(
        self,
        door_api: DoorApiConfig,
        door: chicken_door,
        publisher: DoorMqttPublisher,
    ):
        self.door_api = door_api
        self.door = door
        self.publisher = publisher
        self._lock = asyncio.Lock()

    async def process(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not payload:
            return {"accepted": True, "processed": False}

        required = {"deviceId", "parameterName", "oldValue", "newValue"}
        present = required.intersection(payload)
        if not present:
            return {"accepted": True, "processed": False}
        if present != required:
            raise InvalidWebhookPayload(
                "Payload must include deviceId, parameterName, oldValue, and newValue."
            )

        device_id = _required_string(payload, "deviceId")
        if not secrets.compare_digest(device_id, self.door_api.device_id):
            raise WebhookDeviceMismatch(
                "Webhook device does not match the configured door."
            )

        parameter = _normalize(_required_string(payload, "parameterName"))
        if parameter not in DOOR_STATE_PARAMETERS:
            return {"accepted": True, "processed": False}

        _required_string(payload, "oldValue")
        new_value = _required_string(payload, "newValue")
        position = parse_door_position(new_value)
        if position == door_position.UNKNOWN and _normalize(new_value) != "unknown":
            raise InvalidWebhookPayload(f"Unsupported door state: {new_value}")

        async with self._lock:
            self.door.set_device_state(position)
            await self.publisher.publish_position(position)

        return {
            "accepted": True,
            "processed": True,
            "state": position.value,
        }


def create_omlet_webhook_app(
    webhook_config: OmletWebhookConfig,
    handler: OmletDoorWebhookHandler,
) -> Starlette:
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def receive(request: Request) -> JSONResponse:
        if not _authorized(request.headers.get("authorization"), webhook_config.token):
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        content_type = request.headers.get("content-type", "")
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            return JSONResponse(
                {"error": "unsupported_content_type"},
                status_code=415,
            )

        try:
            body = await _read_limited_body(request)
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise InvalidWebhookPayload("Webhook payload must be a JSON object.")
            result = await handler.process(payload)
        except WebhookBodyTooLarge:
            return JSONResponse({"error": "payload_too_large"}, status_code=413)
        except (json.JSONDecodeError, UnicodeDecodeError, InvalidWebhookPayload) as exc:
            return JSONResponse(
                {"error": "invalid_payload", "detail": str(exc)},
                status_code=400,
            )
        except WebhookDeviceMismatch:
            return JSONResponse({"error": "device_mismatch"}, status_code=403)
        except Exception:
            logger.exception("Omlet webhook state publication failed.")
            return JSONResponse({"error": "publication_failed"}, status_code=503)

        return JSONResponse(result)

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route(OMLET_WEBHOOK_PATH, receive, methods=["POST"]),
        ]
    )


class OmletWebhookServer:
    endpoint_path = OMLET_WEBHOOK_PATH

    def __init__(
        self,
        http_config: HttpConfig,
        webhook_config: OmletWebhookConfig,
        handler: OmletDoorWebhookHandler,
    ):
        self.http_config = http_config
        self.app = create_omlet_webhook_app(webhook_config, handler)
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return bool(
            self._server is not None
            and self._server.started
            and self._task is not None
            and not self._task.done()
        )

    async def start(self):
        configuration = uvicorn.Config(
            self.app,
            host=self.http_config.host,
            port=self.http_config.port,
            access_log=False,
            log_level="warning",
        )
        self._server = uvicorn.Server(configuration)
        self._task = asyncio.create_task(self._serve())

        try:
            await asyncio.wait_for(self._wait_until_started(), timeout=5)
        except Exception:
            await self._clean_up_failed_start()
            raise

    async def stop(self):
        if self._server is None or self._task is None:
            return
        self._server.should_exit = True
        await self._task
        self._task = None
        self._server = None

    async def _serve(self):
        try:
            if self._server is not None:
                await self._server.serve()
        except SystemExit as exc:
            address = f"{self.http_config.host}:{self.http_config.port}"
            raise RuntimeError(
                f"Omlet webhook listener could not start on {address}. "
                "The address may already be in use or blocked by the operating system."
            ) from exc

    async def _clean_up_failed_start(self):
        if self._server is not None:
            self._server.should_exit = True
        if self._task is not None and not self._task.done():
            await self._task
        self._task = None
        self._server = None

    async def _wait_until_started(self):
        while self._server is not None and not self._server.started:
            if self._task is not None and self._task.done():
                await self._task
            await asyncio.sleep(0.01)


async def _read_limited_body(request: Request) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            parsed_content_length = int(content_length)
        except ValueError as exc:
            raise InvalidWebhookPayload("Content-Length must be an integer.") from exc
        if parsed_content_length > MAX_WEBHOOK_BODY_BYTES:
            raise WebhookBodyTooLarge

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BODY_BYTES:
            raise WebhookBodyTooLarge
    return bytes(body)


def _authorized(header: str | None, expected_token: str) -> bool:
    if not header or not expected_token:
        return False
    supplied = header.strip()
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    return secrets.compare_digest(supplied, expected_token)


def _required_string(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidWebhookPayload(f"{name} must be a non-empty string.")
    return value.strip()


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())
