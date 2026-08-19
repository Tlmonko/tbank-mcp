from __future__ import annotations

import json

from tbank_cli.__main__ import main


def test_auth_status_is_json_and_secret_free(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("TBANK_SESSION_FILE", str(tmp_path / "session.json"))
    assert main(["auth", "status", "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "missing"}
    assert captured.err == ""


def test_invalid_operation_is_json_on_stderr(capsys) -> None:
    assert (
        main(
            [
                "operations",
                "list",
                "--account",
                "acct",
                "--from",
                "bad",
                "--to",
                "2026-08-02",
                "--json",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert json.loads(captured.err)["error"]
    assert "bad" not in captured.err


def test_help_commands_exist(capsys) -> None:
    assert main(["products", "list", "--help"]) == 0
    assert "usage:" in capsys.readouterr().out


def test_argparse_errors_are_json(capsys) -> None:
    assert main(["operations", "list"]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.err)["error"]
