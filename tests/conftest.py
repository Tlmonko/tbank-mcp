from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tbank_cli.session import SessionStore


@pytest.fixture
def session_file(tmp_path: Path) -> Path:
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps(
            {
                "cookies": {"synthetic": "fixture"},
                "session_id": "synthetic-session",
                "expires_at": "2099-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def session_store(session_file: Path) -> SessionStore:
    return SessionStore(session_file)


@pytest.fixture
def fake_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"path": request.url.path, "query": dict(request.url.params)}
        return httpx.Response(200, json=payload, request=request)

    return httpx.MockTransport(handler)
