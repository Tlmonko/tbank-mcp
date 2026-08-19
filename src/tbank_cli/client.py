"""Жёстко ограниченный read-only HTTP клиент текущего web API Т‑Банка.

Пути и fixed query сверены по загруженному в авторизованном личном кабинете
web-клиенту. Произвольные URL, методы, заголовки и тела запроса не принимаются.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

import httpx

from .models import AccountRef, OperationQuery, OperationRef
from .session import DEFAULT_ORIGIN, SessionStore

ENDPOINTS: Mapping[str, str] = {
    "products": "/api/common/v1/accounts_light_ib",
    "accounts": "/api/common/v1/accounts_light_ib",
    "operations": "/mybank/api/operations/timeline/public/legacy/v1/operations",
    "operation": "/mybank/api/operations/timeline/public/legacy/v1/operations",
    "receipt": "/api/common/v1/shopping_receipt",
    "statements": "/api/common/v1/statements",
}

READ_ONLY_METHODS = frozenset({"GET"})
PARAMETER_KEYS: Mapping[str, frozenset[str]] = {
    "products": frozenset({"appName", "appVersion", "platform", "sessionid", "origin"}),
    "accounts": frozenset({"appName", "appVersion", "platform", "sessionid", "origin"}),
    "operations": frozenset(
        {"appName", "appVersion", "origin", "sessionid", "account", "start", "end"}
    ),
    "operation": frozenset({"appName", "appVersion", "origin", "sessionid", "operationId"}),
    "receipt": frozenset({"operationId", "sessionid"}),
    "statements": frozenset({"account", "itemsOrder", "sessionid"}),
}
SESSION_HEADER_ALLOWLIST = frozenset(
    {"accept", "content-type", "referer", "user-agent", "x-csrf-token", "x-requested-with"}
)
SECRET_PATTERN = re.compile(
    r"(?i)\b(?:authorization|cookie|token|session(?:[-_ ]?(?:id|token))?|bearer|password|otp|sms)"
    r"\s*[:=]\s*[^\s,;]+"
)


class ClientError(RuntimeError):
    """Редактируемая ошибка клиента."""


class ReadOnlyTbankClient:
    def __init__(
        self,
        session: SessionStore | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.session = session or SessionStore()
        self._http = httpx.Client(
            base_url="https://www.tbank.ru", transport=transport, timeout=20.0
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ReadOnlyTbankClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, endpoint_name: str, params: Mapping[str, str | int]) -> Any:
        if endpoint_name not in ENDPOINTS:
            raise ClientError("unknown endpoint")
        if frozenset(params) != PARAMETER_KEYS[endpoint_name]:
            raise ClientError("invalid fixed request parameters")
        path = ENDPOINTS[endpoint_name]
        # The only method here is a fixed GET; callers cannot supply URL/method/body.
        try:
            material = self.session.load()
            cookies = material.get("cookies", {})
            raw_headers = material.get("headers", {})
            headers = {
                str(key): str(value)
                for key, value in raw_headers.items()
                if str(key).lower() in SESSION_HEADER_ALLOWLIST
            }
            response = self._http.get(path, params=dict(params), cookies=cookies, headers=headers)
        except (httpx.HTTPError, OSError) as exc:
            raise ClientError("request failed") from exc
        if response.status_code >= 400:
            raise ClientError(f"request failed with status {response.status_code}")
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ClientError("response was not JSON") from exc

    @staticmethod
    def _session_params(material: Mapping[str, Any], *, platform: bool = False) -> dict[str, str]:
        params = {
            "appName": "supreme",
            "appVersion": "0.0.1",
            "origin": str(material.get("origin", DEFAULT_ORIGIN)),
            "sessionid": str(material["session_id"]),
        }
        if platform:
            params["platform"] = "web"
        return params

    def _material(self) -> dict[str, Any]:
        return self.session.load()

    def list_products(self) -> Any:
        return self._request("products", self._session_params(self._material(), platform=True))

    def list_accounts(self) -> Any:
        return self._request("accounts", self._session_params(self._material(), platform=True))

    def list_operations(self, query: OperationQuery) -> Any:
        params = self._session_params(self._material())
        params.update(
            {
                "account": query.account_id,
                "start": str(query.start_milliseconds),
                "end": str(query.end_milliseconds),
            }
        )
        return self._request(
            "operations",
            params,
        )

    def get_operation(self, ref: OperationRef) -> Any:
        params = self._session_params(self._material())
        params["operationId"] = ref.operation_id
        return self._request("operation", params)

    def get_receipt(self, ref: OperationRef) -> Any:
        material = self._material()
        return self._request(
            "receipt", {"operationId": ref.operation_id, "sessionid": str(material["session_id"])}
        )

    def list_statements(self, ref: AccountRef) -> Any:
        material = self._material()
        return self._request(
            "statements",
            {
                "account": ref.account_id,
                "itemsOrder": "desc",
                "sessionid": str(material["session_id"]),
            },
        )


def redact_error(error: BaseException) -> str:
    """Сделать диагностическую строку безопасной для stderr."""
    text = str(error)
    text = SECRET_PATTERN.sub("[REDACTED]", text)
    return text[:300] or "request failed"
