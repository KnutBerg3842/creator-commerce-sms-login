from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CodeRequest:
    phone: str
    login_id: str

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "CodeRequest":
        return cls(phone=_required(value, "phone"), login_id=_required(value, "login_id"))


@dataclass(frozen=True)
class CodeVerification:
    phone: str
    code: str
    login_id: str
    creator_id: str
    asset_id: str

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "CodeVerification":
        return cls(
            phone=_required(value, "phone"),
            code=_required(value, "code"),
            login_id=_required(value, "login_id"),
            creator_id=_required(value, "creator_id"),
            asset_id=_required(value, "asset_id"),
        )


@dataclass(frozen=True)
class LoginPlan:
    login_id: str
    authenticated: bool
    digital_asset_delivery: str
    subscriber_update: str
    content_processing: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _required(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return item.strip()
