import httpx

from media_key_drill.infrai_client import InfraiClient


def test_client_decodes_429_envelope_then_retries() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer env-secret"
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "3"},
                json={"ok": False, "data": None, "error": {"code": "RATE_LIMIT"}, "metadata": {}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"entries": []}, "error": None, "metadata": {}},
        )

    with InfraiClient(
        "env-secret", transport=httpx.MockTransport(handler), sleep=delays.append
    ) as client:
        assert client.search_logs() == {"entries": []}

    assert delays == [3.0]

