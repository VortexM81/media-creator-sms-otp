from media_login.login_service import LoginService
from media_login.media_workflow import AssetState, MediaWorkflow


class AcceptedOtp:
    def request_otp(self, phone: str, request_id: str) -> dict[str, str]:
        return {"request_id": request_id}

    def verify_otp(self, phone: str, code: str, request_id: str) -> dict[str, bool]:
        return {"verified": code == "246810"}


def test_ready_asset_is_delivered_only_after_creator_otp_verification() -> None:
    login = LoginService(AcceptedOtp())
    media = MediaWorkflow()
    media.ingest("asset-42", "creator-7", "pilot.mov")
    media.start_processing("asset-42", "job-9")
    media.complete_processing("asset-42")

    verified = login.verify_code("+15550101010", "246810", "verify-001")
    delivered = media.deliver("asset-42", "creator-7", verified)

    assert delivered.state == AssetState.DELIVERED
