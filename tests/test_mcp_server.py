from __future__ import annotations

import importlib

import pytest


def test_mcp_module_has_exact_read_only_tool_names() -> None:
    pytest.importorskip("mcp")
    module = importlib.import_module("tbank_cli.mcp_server")
    module = importlib.reload(module)
    if module.mcp is None:
        pytest.skip("MCP SDK unavailable")
    tools = module.mcp._tool_manager.list_tools()
    names = {tool.name for tool in tools}
    assert names == {
        "list_products",
        "list_accounts",
        "list_operations",
        "get_operation",
        "get_receipt",
        "list_statements",
    }
