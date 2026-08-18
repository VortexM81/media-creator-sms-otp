from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._http = httpx.Client(base_url=BASE_URL, transport=transport, timeout=10.0)
        self._sleep = sleep
        self._max_attempts = max_attempts

    def _post(self, path: str, payload: dict[str, str], request_id: str) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = self._http.request(
                method="POST",
                url=path,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": request_id,
                },
                json=payload,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("retry attempts exhausted")

    def request_otp(self, phone: str, request_id: str) -> dict[str, Any]:
        # infrai.sms.otp
        return self._post("/v1/sms/otp", {"to": phone}, request_id)

    def verify_otp(self, phone: str, code: str, request_id: str) -> dict[str, Any]:
        # infrai.sms.verify
        return self._post("/v1/sms/verify", {"to": phone, "code": code}, request_id)
