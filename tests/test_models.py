from __future__ import annotations

import pytest

from tbank_cli.models import OperationQuery, ValidationError, normalize_date


def test_normalize_date() -> None:
    assert normalize_date("2026-08-01", "from") == "2026-08-01"


@pytest.mark.parametrize("value", ["01.08.2026", "2026/08/01", "nope"])
def test_rejects_non_iso_date(value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_date(value, "from")


def test_operation_query_validates_order_and_normalizes_to_epoch_milliseconds() -> None:
    with pytest.raises(ValidationError):
        OperationQuery("a", "2026-08-02", "2026-08-01")
    query = OperationQuery("a", "2026-08-01", "2026-08-02")
    assert query.date_from == "2026-08-01"
    assert query.start_milliseconds == 1785542400000
    assert query.end_milliseconds == 1785715199999
