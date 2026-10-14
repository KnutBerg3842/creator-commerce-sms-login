from __future__ import annotations

import io
import json
import urllib.error

import pytest

from creator_login.infrai_sms import InfraiSms
from creator_login.models import CodeVerification
from creator_login.workflow import CreatorLoginService


class RecordingSms:
    def __init__(self) -> None:
        self.verified: list[tuple[str, str, str]] = []

    def otp(self, *, to: str, idempotency_key: str) -> dict[str, object]:
        return {}

    def verify(
        self, *, to: str, code: str, idempotency_key: str
    ) -> dict[str, object]:
        self.verified.append((to, code, idempotency_key))
        return {"verified": True}


def test_verified_login_releases_creator_work() -> None:
    sms = RecordingSms()
    service = CreatorLoginService(sms)

    plan = service.verify_code(
        CodeVerification(
            phone="+15551234567",
            code="481205",
            login_id="login-7",
            creator_id="creator-42",
            asset_id="course-101",
        )
    )

    assert sms.verified == [("+15551234567", "481205", "login-verify:login-7")]
    assert plan.to_dict() == {
        "login_id": "login-7",
        "authenticated": True,
        "digital_asset_delivery": "release:course-101",
        "subscriber_update": "mark_active:creator-42",
        "content_processing": "enqueue:course-101",
    }


def test_unverified_login_does_not_release_creator_work() -> None:
    sms = RecordingSms()
    sms.verify = lambda **_: {"verified": False}  # type: ignore[method-assign]
    service = CreatorLoginService(sms)

    with pytest.raises(ValueError, match="verification failed"):
        service.verify_code(
            CodeVerification(
                phone="+15551234567",
                code="000000",
                login_id="login-7",
                creator_id="creator-42",
                asset_id="course-101",
            )
        )


class FakeResponse:
    def __init__(self, body: dict[str, object], status: int = 200) -> None:
        self.status = status
        self.headers: dict[str, str] = {}
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_otp_retry_keeps_method_and_request_identity() -> None:
    requests: list[object] = []

    def opener(request: object, timeout: int) -> FakeResponse:
        requests.append(request)
        if len(requests) == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                {"Retry-After": "0"},
                io.BytesIO(
                    b'{"ok":false,"data":null,"error":{},"metadata":{}}'
                ),
            )
        return FakeResponse({"ok": True, "data": {"sent": True}, "metadata": {}})

    client = InfraiSms(api_key="test-key", opener=opener, sleep=lambda _: None)
    assert client.otp(to="+15551234567", idempotency_key="login-code:login-7") == {
        "sent": True
    }
    assert [request.method for request in requests] == ["POST", "POST"]
    assert [request.headers["Idempotency-key"] for request in requests] == [
        "login-code:login-7",
        "login-code:login-7",
    ]
