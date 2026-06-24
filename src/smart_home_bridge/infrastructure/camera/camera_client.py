from abc import ABC, abstractmethod
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from smart_home_bridge.config import CameraConfig


class CameraClientInterface(ABC):
    @abstractmethod
    def fetch_jpeg(self) -> bytes:
        pass

    @abstractmethod
    def health(self) -> bool:
        pass


class CameraClient(CameraClientInterface):
    def __init__(self, config: CameraConfig):
        self.config = config
        self.client = build_opener()

    def fetch_jpeg(self) -> bytes:
        status_code, headers, body = self._get(self.config.jpg_endpoint)
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(f"Camera JPEG request failed with HTTP {status_code}")

        content_type = _header_value(headers, "Content-Type")
        if content_type and not content_type.lower().startswith("image/jpeg"):
            raise RuntimeError(f"Camera JPEG request returned unexpected content type: {content_type}")

        if not body.startswith(b"\xff\xd8"):
            raise RuntimeError("Camera JPEG request did not return JPEG bytes")

        return body

    def health(self) -> bool:
        try:
            status_code, _headers, _body = self._get(self.config.health_endpoint)
        except RuntimeError:
            return False

        return 200 <= status_code < 300

    def _get(self, endpoint: str) -> tuple[int, dict[str, str], bytes]:
        request = Request(
            self._build_url(endpoint),
            headers={"Accept": "image/jpeg"},
            method="GET",
        )

        try:
            with self.client.open(request, timeout=self.config.timeout_seconds) as response:
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()
        except URLError as exc:
            raise RuntimeError(f"Camera GET request failed for {endpoint}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError(f"Camera GET request timed out for {endpoint}") from exc

    def _build_url(self, endpoint: str) -> str:
        base_url = f"http://{self.config.host}:{self.config.port}"
        return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def _header_value(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value

    return None
