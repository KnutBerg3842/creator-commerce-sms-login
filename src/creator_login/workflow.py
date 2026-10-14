from __future__ import annotations

from .infrai_sms import InfraiSms
from .models import CodeRequest, CodeVerification, LoginPlan


class CreatorLoginService:
    def __init__(self, sms: InfraiSms) -> None:
        self.sms = sms

    def request_code(self, request: CodeRequest) -> dict[str, str]:
        self.sms.otp(to=request.phone, idempotency_key=f"login-code:{request.login_id}")
        return {"login_id": request.login_id, "status": "code_sent"}

    def verify_code(self, request: CodeVerification) -> LoginPlan:
        verification = self.sms.verify(
            to=request.phone,
            code=request.code,
            idempotency_key=f"login-verify:{request.login_id}",
        )
        if verification.get("verified") is not True:
            raise ValueError("verification failed")
        return LoginPlan(
            login_id=request.login_id,
            authenticated=True,
            digital_asset_delivery=f"release:{request.asset_id}",
            subscriber_update=f"mark_active:{request.creator_id}",
            content_processing=f"enqueue:{request.asset_id}",
        )
