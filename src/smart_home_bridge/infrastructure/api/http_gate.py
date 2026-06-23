from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from smart_home_bridge.config import HttpConfig


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    body: str

    def json(self) -> Any:
        return json.loads(self.body)


class HttpGateInterface(ABC):
    @abstractmethod
    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> HttpResponse:
        pass

    @abstractmethod
    def post(self, endpoint: str, data: Any | None = None) -> HttpResponse:
        pass

    @abstractmethod
    def put(self, endpoint: str, data: Any | None = None) -> HttpResponse:
        pass

    @abstractmethod
    def delete(self, endpoint: str) -> HttpResponse:
        pass


class HttpGate(HttpGateInterface):
    def __init__(self, http_config: HttpConfig, timeout: float = 10):
        self.config = http_config
        self.timeout = timeout
        self.client = build_opener()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> HttpResponse:
        return self._send("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Any | None = None) -> HttpResponse:
        return self._send("POST", endpoint, data=data)

    def put(self, endpoint: str, data: Any | None = None) -> HttpResponse:
        return self._send("PUT", endpoint, data=data)

    def delete(self, endpoint: str) -> HttpResponse:
        return self._send("DELETE", endpoint)

    def _send(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
    ) -> HttpResponse:
        request = Request(
            self._build_url(endpoint, params),
            data=self._encode_body(data),
            headers=self._build_headers(data),
            method=method,
        )

        try:
            with self.client.open(request, timeout=self.timeout) as response:
                return self._build_response(response.status, response.headers, response.read())
        except HTTPError as exc:
            return self._build_response(exc.code, exc.headers, exc.read())
        except URLError as exc:
            raise RuntimeError(f"HTTP {method} request failed for {endpoint}: {exc.reason}") from exc

    def _build_url(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        base_url = f"http://{self.config.host}:{self.config.port}"
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"

        return url

    def _encode_body(self, data: Any | None) -> bytes | None:
        if data is None:
            return None

        if isinstance(data, bytes):
            return data

        if isinstance(data, str):
            return data.encode("utf-8")

        return json.dumps(data).encode("utf-8")

    def _build_headers(self, data: Any | None) -> dict[str, str]:
        headers = {"Accept": "application/json"}

        if data is not None and not isinstance(data, bytes):
            headers["Content-Type"] = "application/json"

        return headers

    def _build_response(self, status_code, headers, body: bytes) -> HttpResponse:
        return HttpResponse(
            status_code=status_code,
            headers=dict(headers.items()),
            body=body.decode("utf-8"),
        )
