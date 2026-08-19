"""CLI entry point с JSON-first выводом."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .client import ClientError, ReadOnlyTbankClient, redact_error
from .models import AccountRef, OperationQuery, OperationRef, ValidationError
from .session import SessionError, SessionStore


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _json_print({"error": message}, stream=sys.stderr)
        raise SystemExit(2)


def _json_print(value: Any, stream: Any | None = None) -> None:
    stream = stream or sys.stdout
    json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
    stream.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="tbank", description="Локальный read-only CLI Т‑Банка")
    sub = parser.add_subparsers(dest="resource", required=True, parser_class=JsonArgumentParser)

    auth = sub.add_parser("auth", help="Статус и безопасный импорт сессии")
    auth_sub = auth.add_subparsers(dest="action", required=True)
    auth_status = auth_sub.add_parser("status", help="Показать только статус сессии")
    auth_status.add_argument("--json", action="store_true", help="JSON output")
    auth_import = auth_sub.add_parser(
        "import", help="Импортировать локальный export браузерной сессии"
    )
    auth_import.add_argument("source", type=Path)
    auth_import.add_argument("--replace", action="store_true")
    auth_import.add_argument("--json", action="store_true", help="JSON output")

    for resource, help_text in (("products", "Продукты"), ("accounts", "Счета и карты")):
        cmd = sub.add_parser(resource, help=help_text)
        cmd_sub = cmd.add_subparsers(dest="action", required=True)
        action = cmd_sub.add_parser("list", help=f"Получить {help_text.lower()}")
        action.add_argument("--json", action="store_true", help="JSON output")

    operations = sub.add_parser("operations", help="Операции")
    op_sub = operations.add_subparsers(dest="action", required=True)
    op_list = op_sub.add_parser("list", help="Получить операции за период")
    op_list.add_argument("--account", required=True, dest="account_id")
    op_list.add_argument("--from", required=True, dest="date_from")
    op_list.add_argument("--to", required=True, dest="date_to")
    op_list.add_argument("--json", action="store_true", help="JSON output")

    for resource, action_name, help_text in (
        ("operation", "get", "Получить детали операции"),
        ("receipt", "get", "Получить чек операции"),
    ):
        command = sub.add_parser(resource, help=help_text)
        command_sub = command.add_subparsers(dest="action", required=True)
        get = command_sub.add_parser(action_name, help=help_text)
        get.add_argument(
            "--id" if resource == "operation" else "--operation",
            dest="operation_id",
            required=True,
        )
        get.add_argument("--json", action="store_true", help="JSON output")

    statements = sub.add_parser("statements", help="Выписки")
    statements_sub = statements.add_subparsers(dest="action", required=True)
    statements_list = statements_sub.add_parser("list", help="Получить выписки")
    statements_list.add_argument("--account", required=True, dest="account_id")
    statements_list.add_argument("--json", action="store_true", help="JSON output")
    return parser


def _client() -> ReadOnlyTbankClient:
    return ReadOnlyTbankClient(SessionStore())


def run(args: argparse.Namespace) -> int:
    store = SessionStore()
    try:
        if args.resource == "auth" and args.action == "status":
            _json_print({"status": store.status()})
            return 0
        if args.resource == "auth" and args.action == "import":
            store.import_file(args.source, replace=args.replace)
            _json_print({"status": "imported"})
            return 0

        with _client() as client:
            if args.resource == "products":
                result = client.list_products()
            elif args.resource == "accounts":
                result = client.list_accounts()
            elif args.resource == "operations":
                result = client.list_operations(
                    OperationQuery(args.account_id, args.date_from, args.date_to)
                )
            elif args.resource in {"operation", "receipt"}:
                ref = OperationRef(args.operation_id)
                result = (
                    client.get_operation(ref)
                    if args.resource == "operation"
                    else client.get_receipt(ref)
                )
            elif args.resource == "statements":
                result = client.list_statements(AccountRef(args.account_id))
            else:
                raise ValidationError("unsupported command")
        _json_print(result)
        return 0
    except (ValidationError, SessionError, ClientError) as exc:
        _json_print({"error": redact_error(exc)}, stream=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
