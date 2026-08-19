from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from tbank_cli.session import SessionError, SessionStore


def test_session_status_does_not_expose_secret(session_store: SessionStore) -> None:
    assert session_store.status() == "authenticated"
    assert "synthetic" not in session_store.status()


def test_import_sets_0600_and_requires_replace(tmp_path: Path, session_store: SessionStore) -> None:
    source = tmp_path / "export.json"
    source.write_text(
        json.dumps({"cookies": {"secret": "never-print"}, "session_id": "synthetic-session"}),
        encoding="utf-8",
    )
    with pytest.raises(SessionError, match="already exists"):
        session_store.import_file(source)
    session_store.import_file(source, replace=True)
    mode = stat.S_IMODE(os.stat(session_store.path).st_mode)
    assert mode == 0o600
    assert session_store.status() == "authenticated"


def test_missing_and_expired_status(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "missing.json")
    assert store.status() == "missing"
    store.path.write_text(
        json.dumps(
            {"cookies": {}, "session_id": "synthetic-session", "expires_at": "2000-01-01T00:00:00Z"}
        ),
        encoding="utf-8",
    )
    assert store.status() == "expired"


def test_session_without_id_is_not_authenticated(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"cookies": {}}), encoding="utf-8")
    assert SessionStore(path).status() == "expired"
