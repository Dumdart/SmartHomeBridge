from urllib.error import HTTPError, URLError

from smart_home_bridge.config import CameraConfig
from smart_home_bridge.infrastructure.camera import CameraClient, CameraClientInterface


JPEG_BYTES = b"\xff\xd8\xff\xe0frame-data"


class FakeHeaders:
    def __init__(self, values=None):
        self.values = values or {"Content-Type": "image/jpeg"}

    def items(self):
        return self.values.items()


class FakeResponse:
    def __init__(self, status=200, body=JPEG_BYTES, headers=None):
        self.status = status
        self.body = body
        self.headers = headers or FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body

    def close(self):
        pass


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse()
        self.error = error
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        if self.error:
            raise self.error

        return self.response


def test_camera_client_implements_interface():
    client = CameraClient(CameraConfig())

    assert isinstance(client, CameraClientInterface)


def test_fetch_jpeg_returns_binary_body():
    client = CameraClient(CameraConfig(host="esp32cam.local", timeout_seconds=2.5))
    fake_client = FakeClient()
    client.client = fake_client

    body = client.fetch_jpeg()

    assert body == JPEG_BYTES
    assert fake_client.request.full_url == "http://esp32cam.local:80/jpg"
    assert fake_client.request.get_method() == "GET"
    assert fake_client.timeout == 2.5


def test_fetch_jpeg_rejects_http_failure():
    error = HTTPError(
        url="http://esp32cam.local:80/jpg",
        code=500,
        msg="Server Error",
        hdrs=FakeHeaders(),
        fp=FakeResponse(body=b"error"),
    )
    client = CameraClient(CameraConfig(host="esp32cam.local"))
    client.client = FakeClient(error=error)

    try:
        client.fetch_jpeg()
    except RuntimeError as exc:
        assert str(exc) == "Camera JPEG request failed with HTTP 500"
    else:
        raise AssertionError("Expected HTTP failure to be rejected")


def test_fetch_jpeg_rejects_timeout_failure():
    client = CameraClient(CameraConfig(host="esp32cam.local"))
    client.client = FakeClient(error=URLError(TimeoutError("timed out")))

    try:
        client.fetch_jpeg()
    except RuntimeError as exc:
        assert "Camera GET request failed for /jpg" in str(exc)
    else:
        raise AssertionError("Expected timeout failure to be rejected")


def test_fetch_jpeg_rejects_non_jpeg_content_type():
    client = CameraClient(CameraConfig(host="esp32cam.local"))
    client.client = FakeClient(
        response=FakeResponse(headers=FakeHeaders({"Content-Type": "text/plain"}))
    )

    try:
        client.fetch_jpeg()
    except RuntimeError as exc:
        assert str(exc) == "Camera JPEG request returned unexpected content type: text/plain"
    else:
        raise AssertionError("Expected content type failure to be rejected")


def test_fetch_jpeg_accepts_jpeg_content_type_with_parameters():
    client = CameraClient(CameraConfig(host="esp32cam.local"))
    client.client = FakeClient(
        response=FakeResponse(headers=FakeHeaders({"Content-Type": "image/jpeg; charset=binary"}))
    )

    assert client.fetch_jpeg() == JPEG_BYTES


def test_health_returns_false_when_camera_request_fails():
    client = CameraClient(CameraConfig(host="esp32cam.local"))
    client.client = FakeClient(error=URLError("unreachable"))

    assert client.health() is False
