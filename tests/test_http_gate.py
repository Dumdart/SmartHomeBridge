from urllib.error import HTTPError

from loxone_bridge.config import HttpConfig
from loxone_bridge.infrastructure.api.http_gate import HttpGate, HttpGateInterface


class FakeHeaders:
    def items(self):
        return {"Content-Type": "application/json"}.items()


class FakeResponse:
    def __init__(self, status=200, body=b'{"ok": true}'):
        self.status = status
        self.headers = FakeHeaders()
        self.body = body

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


def test_http_gate_implements_interface():
    gate = HttpGate(HttpConfig(host="localhost", port=8080))

    assert isinstance(gate, HttpGateInterface)


def test_get_sends_query_params():
    gate = HttpGate(HttpConfig(host="localhost", port=8080), timeout=2)
    client = FakeClient()
    gate.client = client

    response = gate.get("/health", {"verbose": "true"})

    assert client.request.full_url == "http://localhost:8080/health?verbose=true"
    assert client.request.get_method() == "GET"
    assert client.timeout == 2
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_post_sends_json_body():
    gate = HttpGate(HttpConfig(host="localhost", port=8080))
    client = FakeClient()
    gate.client = client

    gate.post("/door/open", {"command_id": "abc"})

    assert client.request.full_url == "http://localhost:8080/door/open"
    assert client.request.get_method() == "POST"
    assert client.request.data == b'{"command_id": "abc"}'
    assert client.request.headers["Content-type"] == "application/json"


def test_http_error_returns_response():
    error = HTTPError(
        url="http://localhost:8080/missing",
        code=404,
        msg="Not Found",
        hdrs=FakeHeaders(),
        fp=FakeResponse(body=b'{"error": "missing"}'),
    )
    gate = HttpGate(HttpConfig(host="localhost", port=8080))
    gate.client = FakeClient(error=error)

    response = gate.get("/missing")

    assert response.status_code == 404
    assert response.json() == {"error": "missing"}
