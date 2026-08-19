"""Типизированные входы и безопасные служебные модели."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any


class ValidationError(ValueError):
    """Ошибка безопасной валидации пользовательского параметра."""


def validate_identifier(value: str, name: str) -> str:
    value = value.strip()
    if not value or len(value) > 128:
        raise ValidationError(f"{name} must be a non-empty identifier")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise ValidationError(f"{name} contains unsupported characters")
    return value


def normalize_date(value: str, name: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{name} must use YYYY-MM-DD") from exc
    return parsed.isoformat()


def public_json(value: Any) -> Any:
    """Convert dataclasses and nested values to JSON-safe data."""
    if hasattr(value, "__dataclass_fields__"):
        return {key: public_json(item) for key, item in value.__dict__.items()}
    if isinstance(value, dict):
        return {str(key): public_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [public_json(item) for item in value]
    return value


@dataclass(frozen=True)
class OperationQuery:
    account_id: str
    date_from: str
    date_to: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", validate_identifier(self.account_id, "account_id"))
        object.__setattr__(self, "date_from", normalize_date(self.date_from, "from"))
        object.__setattr__(self, "date_to", normalize_date(self.date_to, "to"))
        if self.date_from > self.date_to:
            raise ValidationError("from must be on or before to")

    @property
    def start_milliseconds(self) -> int:
        value = datetime.combine(date.fromisoformat(self.date_from), time.min, tzinfo=UTC)
        return int(value.timestamp() * 1000)

    @property
    def end_milliseconds(self) -> int:
        value = datetime.combine(date.fromisoformat(self.date_to), time.max, tzinfo=UTC)
        return int(value.timestamp() * 1000)


@dataclass(frozen=True)
class AccountRef:
    account_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", validate_identifier(self.account_id, "account_id"))


@dataclass(frozen=True)
class OperationRef:
    operation_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "operation_id", validate_identifier(self.operation_id, "operation_id")
        )
