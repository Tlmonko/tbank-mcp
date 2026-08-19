"""Локальный stdio MCP сервер с шестью read-only инструментами."""

from __future__ import annotations

import sys
from typing import Any

from .client import ClientError, ReadOnlyTbankClient, redact_error
from .models import AccountRef, OperationQuery, OperationRef, ValidationError
from .session import SessionError, SessionStore

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - dependency is declared in pyproject
    FastMCP = None  # type: ignore[assignment,misc]


def _call(method: str, **kwargs: Any) -> Any:
    if method not in {
        "list_products",
        "list_accounts",
        "list_operations",
        "get_operation",
        "get_receipt",
        "list_statements",
    }:
        raise RuntimeError("unknown read-only tool")
    try:
        with ReadOnlyTbankClient(SessionStore()) as client:
            return getattr(client, method)(**kwargs)
    except (ClientError, SessionError, ValidationError) as exc:
        raise RuntimeError(redact_error(exc)) from None


if FastMCP is not None:
    mcp = FastMCP("tbank-cli-mcp")

    @mcp.tool(description="Read-only: list products in the authenticated T‑Bank account.")
    def list_products() -> Any:
        return _call("list_products")

    @mcp.tool(description="Read-only: list accounts and cards.")
    def list_accounts() -> Any:
        return _call("list_accounts")

    @mcp.tool(description="Read-only: list operations for an account and date range.")
    def list_operations(account_id: str, date_from: str, date_to: str) -> Any:
        return _call("list_operations", query=OperationQuery(account_id, date_from, date_to))

    @mcp.tool(description="Read-only: get one operation by operation ID.")
    def get_operation(operation_id: str) -> Any:
        return _call("get_operation", ref=OperationRef(operation_id))

    @mcp.tool(description="Read-only: get a receipt when one is available.")
    def get_receipt(operation_id: str) -> Any:
        return _call("get_receipt", ref=OperationRef(operation_id))

    @mcp.tool(description="Read-only: list available statements for an account.")
    def list_statements(account_id: str) -> Any:
        return _call("list_statements", ref=AccountRef(account_id))
else:
    mcp = None


def main() -> int:
    if mcp is None:
        print("MCP SDK is not installed", file=sys.stderr)
        return 2
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
