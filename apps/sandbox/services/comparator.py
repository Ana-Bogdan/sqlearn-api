from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Iterable


def _canonical_value(value: Any) -> tuple:
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float, Decimal)):
        return ("num", round(float(value), 6))
    # Dates/times and ISO strings are interchangeable: expected results come
    # from JSON (strings) while psycopg returns real date/datetime objects.
    if isinstance(value, (date, datetime, time)):
        return ("text", value.isoformat())
    if isinstance(value, memoryview):
        return ("text", bytes(value).hex())
    if isinstance(value, (bytes, bytearray)):
        return ("text", bytes(value).hex())
    if isinstance(value, str):
        return ("text", value.strip())
    return ("text", str(value))


def _canonical_row(row: Iterable[Any]) -> tuple:
    return tuple(_canonical_value(v) for v in row)


def _canonical_columns(columns: Iterable[str]) -> list[str]:
    return [(c or "").strip().lower() for c in columns]


def compare_results(expected: dict, actual: dict) -> tuple[bool, str | None]:
    """Compare an actual query result against an exercise's expected result.

    Normalisation rules:
    - column names: trimmed, compared case-insensitively, order preserved.
    - row cell equality: None stays None; numeric types collapse onto float
      with 6-digit precision; date/time values compared by ISO string; strings
      trimmed. Ordering across rows ignored unless ``expected["order_matters"]``.

    Returns ``(is_correct, reason_or_none)`` where ``reason`` explains why a
    comparison failed so the caller can surface it as a differentiated error.
    """
    expected_cols = _canonical_columns(expected.get("columns") or [])
    actual_cols = _canonical_columns(actual.get("columns") or [])
    expected_rows_raw = list(expected.get("rows") or [])
    actual_rows_raw = list(actual.get("rows") or [])
    order_matters = bool(expected.get("order_matters", False))

    if expected_cols != actual_cols:
        return False, "columns_mismatch"

    if len(expected_rows_raw) != len(actual_rows_raw):
        return False, "row_count_mismatch"

    expected_rows = [_canonical_row(r) for r in expected_rows_raw]
    actual_rows = [_canonical_row(r) for r in actual_rows_raw]

    if not order_matters:
        expected_rows.sort()
        actual_rows.sort()

    if expected_rows != actual_rows:
        return False, "rows_mismatch"

    return True, None
