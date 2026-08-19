from __future__ import annotations

import inspect

import httpx
import pytest

from tbank_cli.client import ClientError, ReadOnlyTbankClient, redact_error
from tbank_cli.models import AccountRef, OperationQuery, OperationRef


def test_allowlisted_get_endpoints_and_fixed_parameters(session_store, fake_transport) -> None:
    with ReadOnlyTbankClient(session_store, transport=fake_transport) as client:
        assert client.list_products()["path"] == "/api/common/v1/accounts_light_ib"
        assert client.list_accounts()["query"]["platform"] == "web"
        assert client.list_accounts()["query"]["sessionid"] == "synthetic-session"

        operations = client.list_operations(OperationQuery("acct-1", "2026-08-01", "2026-08-02"))
        assert operations["path"].endswith("/public/legacy/v1/operations")
        assert operations["query"]["account"] == "acct-1"
        assert operations["query"]["start"] == "1785542400000"
        assert operations["query"]["end"] == "1785715199999"
        assert client.get_operation(OperationRef("op-1"))["query"]["operationId"] == "op-1"
        assert client.get_receipt(OperationRef("op-1"))["path"].endswith("shopping_receipt")
        statements = client.list_statements(AccountRef("acct-1"))
        assert statements["query"] == {
            "account": "acct-1",
            "itemsOrder": "desc",
            "sessionid": "synthetic-session",
        }


def test_unknown_endpoints_and_parameters_are_blocked(session_store, fake_transport) -> None:
    with ReadOnlyTbankClient(session_store, transport=fake_transport) as client:
        with pytest.raises(ClientError, match="unknown"):
            client._request("arbitrary", {})
        with pytest.raises(ClientError, match="fixed request parameters"):
            client._request("products", {"unexpected": "value"})


def test_request_surface_is_not_generic() -> None:
    signature = inspect.signature(ReadOnlyTbankClient._request)
    assert "method" not in signature.parameters
    assert "url" not in signature.parameters
    assert "body" not in signature.parameters
    constructor = inspect.signature(ReadOnlyTbankClient)
    assert "base_url" not in constructor.parameters


def test_only_get_is_allowed() -> None:
    from tbank_cli.client import READ_ONLY_METHODS

    assert READ_ONLY_METHODS == {"GET"}


def test_http_error_does_not_include_response_body(session_store) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="cookie=real-secret account=real-data", request=request)

    with ReadOnlyTbankClient(session_store, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ClientError) as error:
            client.list_products()
    assert "real-secret" not in str(error.value)
    assert "real-data" not in str(error.value)


def test_redact_error_hides_secret_values() -> None:
    message = redact_error(ValueError("cookie=real-secret token=abc123"))
    assert "real-secret" not in message
    assert "abc123" not in message
