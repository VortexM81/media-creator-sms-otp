from __future__ import annotations

from typing import Any, Protocol


class SmsOtp(Protocol):
    def request_otp(self, phone: str, request_id: str) -> dict[str, Any]:
        """Request a code for one login attempt."""

    def verify_otp(self, phone: str, code: str, request_id: str) -> dict[str, Any]:
        """Return the verification envelope data."""


class LoginService:
    def __init__(self, sms: SmsOtp) -> None:
        self.sms = sms

    def request_code(self, phone: str, request_id: str) -> None:
        self.sms.request_otp(phone, request_id)

    def verify_code(self, phone: str, code: str, request_id: str) -> bool:
        result = self.sms.verify_otp(phone, code, request_id)
        return result.get("verified") is True
