"""Безопасное локальное хранение импортированной браузерной сессии."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SessionError(ValueError):
    """Безопасная ошибка session material без утечки содержимого."""


DEFAULT_SESSION_FILE = Path.home() / ".config" / "tbank-cli" / "session.json"
DEFAULT_ORIGIN = "web,ib5,platform"
ALLOWED_ORIGINS = frozenset({DEFAULT_ORIGIN, f"{DEFAULT_ORIGIN},tjunior"})


def session_path() -> Path:
    configured = os.environ.get("TBANK_SESSION_FILE")
    return Path(configured).expanduser() if configured else DEFAULT_SESSION_FILE


def _is_expired(data: dict[str, Any]) -> bool:
    expires_at = data.get("expires_at")
    if not expires_at:
        return False
    if not isinstance(expires_at, str):
        return True
    try:
        value = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)


def _validate_material(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SessionError("session file must contain a JSON object")
    if not isinstance(data.get("cookies"), (dict, list)):
        raise SessionError("session file must contain cookies")
    if not isinstance(data.get("session_id"), str) or not data["session_id"].strip():
        raise SessionError("session file must contain session_id")
    if len(data["session_id"]) > 4096:
        raise SessionError("session_id is too long")
    if "headers" in data and not isinstance(data["headers"], dict):
        raise SessionError("headers must be an object")
    if "origin" in data and data["origin"] not in ALLOWED_ORIGINS:
        raise SessionError("origin is not supported")
    if "expires_at" in data and not isinstance(data["expires_at"], str):
        raise SessionError("expires_at must be an ISO-8601 string")
    return data


@dataclass
class SessionStore:
    path: Path | None = None

    def __post_init__(self) -> None:
        self.path = (self.path or session_path()).expanduser()

    def status(self) -> str:
        if not self.path.exists():
            return "missing"
        try:
            data = _validate_material(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, SessionError):
            return "expired"
        return "expired" if _is_expired(data) else "authenticated"

    def load(self) -> dict[str, Any]:
        try:
            data = _validate_material(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, SessionError) as exc:
            raise SessionError("unable to read session file") from exc
        if _is_expired(data):
            raise SessionError("session is expired")
        return data

    def import_file(self, source: Path, replace: bool = False) -> None:
        source = source.expanduser()
        if self.path.exists() and not replace:
            raise SessionError("session already exists; pass --replace to overwrite it")
        try:
            data = _validate_material(json.loads(source.read_text(encoding="utf-8")))
        except (OSError, ValueError, SessionError) as exc:
            raise SessionError("invalid session export") from exc
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".session-", dir=self.path.parent)
        try:
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
            os.replace(temporary, self.path)
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise SessionError("unable to store session file") from None
