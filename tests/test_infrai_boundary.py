import httpx

from media_login.infrai_sms import InfraiSmsClient


def test_otp_request_retries_429_with_same_idempotency_key() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"ok": False, "error": {"code": "RETRY_LATER"}})
        return httpx.Response(200, json={"ok": True, "data": {"status": "sent"}, "metadata": {}})

    client = InfraiSmsClient(api_key="test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    result = client.request_otp("+15550101010", "login-001")

    assert result == {"status": "sent"}
    assert [request.headers["Idempotency-Key"] for request in calls] == ["login-001", "login-001"]
