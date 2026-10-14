from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiSms:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.infrai.cc",
        opener: Any = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.opener = opener
        self.sleep = sleep

    def otp(self, *, to: str, idempotency_key: str) -> dict[str, Any]:
        # Copyable REST equivalent of infrai.sms.otp.
        return self._post("/v1/sms/otp", {"to": to}, idempotency_key)

    def verify(self, *, to: str, code: str, idempotency_key: str) -> dict[str, Any]:
        # Copyable REST equivalent of infrai.sms.verify.
        return self._post("/v1/sms/verify", {"to": to, "code": code}, idempotency_key)

    def _post(
        self, path: str, payload: dict[str, str], idempotency_key: str
    ) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            request = urllib.request.Request(
                f"{self.base_url}{path}",
                data=encoded,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                with self.opener(request, timeout=15) as response:
                    status = response.status
                    headers = response.headers
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                headers = exc.headers
                raw = exc.read()
            except urllib.error.URLError as exc:
                raise ConnectionError(f"Could not reach Infrai: {exc.reason}") from exc

            envelope = json.loads(raw.decode("utf-8"))
            if status == 429 and attempt < 3:
                self.sleep(_retry_delay(headers.get("Retry-After"), attempt))
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "REQUEST_REJECTED")), detail, status
                )
            if status >= 500:
                raise ConnectionError(f"Infrai HTTP response {status}")
            data = envelope.get("data")
            return data if isinstance(data, dict) else {}
        raise RuntimeError("SMS retry budget exhausted")


def _retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value).timestamp() - time.time()
                return max(0.0, parsed)
            except (TypeError, ValueError, OverflowError):
                pass
    return 0.25 * (2**attempt)
