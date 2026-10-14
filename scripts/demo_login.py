from __future__ import annotations

import json
import os

from creator_login.infrai_sms import InfraiSms
from creator_login.models import CodeRequest, CodeVerification
from creator_login.workflow import CreatorLoginService


def main() -> None:
    phone = os.environ.get("DEMO_PHONE", "")
    if not phone:
        raise SystemExit("DEMO_PHONE is required")
    service = CreatorLoginService(InfraiSms())
    login_id = "creator-demo-001"
    print(json.dumps(service.request_code(CodeRequest(phone, login_id)), indent=2))
    code = input("Code from SMS: ").strip()
    result = service.verify_code(
        CodeVerification(phone, code, login_id, "creator-42", "course-101")
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
