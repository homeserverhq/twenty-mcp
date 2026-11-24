"""Assertion helpers used by Twenty MCP audit contracts."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any, Iterable

from .mcp_client import AuditError, decode_items


def require(condition: Any, message: str) -> None:
    if not condition:
        raise AuditError(message)


def require_ok(call, label: str = "") -> None:
    if call.is_error:
        raise AuditError(f"{label or call.name} failed: {call.error}")


def require_keys(data: dict[str, Any], *keys: str) -> None:
    require(isinstance(data, dict),
            f"expected a dict response, got {type(data).__name__}")
    missing = [key for key in keys if key not in data]
    require(not missing, f"response is missing keys {missing}; got {sorted(data)}")


def require_list(value: Any, field: str) -> list[Any]:
    require(isinstance(value, list), f"{field} is {type(value).__name__}, expected list")
    return value


def items_of(call, field: str = "items") -> list[Any]:
    return decode_items(call.data, call.name, field)


def find_item(items: Iterable[Any], **fields: Any) -> dict[str, Any]:
    for item in items:
        if isinstance(item, dict) and all(item.get(key) == value for key, value in fields.items()):
            return item
    sample = [
        {key: item.get(key) for key in fields}
        for item in list(items)[:3]
        if isinstance(item, dict)
    ]
    raise AuditError(f"no item matched {fields}; first matches: {sample!r}")


def find_item_ci(items: Iterable[Any], key: str, value: str) -> dict[str, Any]:
    wanted = value.casefold()
    for item in items:
        if isinstance(item, dict) and str(item.get(key, "")).casefold() == wanted:
            return item
    raise AuditError(f"no item with {key}={value!r}")


def _as_datetime(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value, f"{field} is empty ({value!r})")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditError(f"{field} is not ISO 8601: {value!r} ({exc})") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None,
            f"{field} has no UTC offset: {value!r}")
    return parsed


def require_iso(value: Any, field: str) -> str:
    _as_datetime(value, field)
    return value


def require_utc(value: Any, field: str) -> str:
    parsed = _as_datetime(value, field)
    require(parsed.utcoffset() == dt.timedelta(0),
            f"{field} is not UTC: {value!r}")
    return value


def require_instant(value: Any, expected: dt.datetime, field: str) -> str:
    parsed = _as_datetime(value, field)
    require(parsed == expected,
            f"{field} is {value!r}, expected instant {expected.isoformat()}")
    return value


def require_count_eq(data: dict[str, Any], field: str, expected: int) -> None:
    actual = data.get(field)
    require(actual == expected, f"{field} is {actual!r}, expected {expected}")


def require_at_most(value: Any, maximum: int, field: str) -> None:
    require(isinstance(value, int), f"{field} is {type(value).__name__}, expected int")
    require(value <= maximum, f"{field} is {value}, expected <= {maximum}")


def require_not_empty(items: list[Any], label: str) -> None:
    require(bool(items), f"{label} returned an empty list")


def require_empty(items: list[Any], label: str) -> None:
    require(not items, f"{label} returned {len(items)} item(s), expected none")


def require_contains(items: list[Any], label: str, **fields: Any) -> dict[str, Any]:
    try:
        return find_item(items, **fields)
    except AuditError as exc:
        raise AuditError(f"{label}: {exc}") from exc


def require_not_contains(items: list[Any], label: str, **fields: Any) -> None:
    for item in items:
        if isinstance(item, dict) and all(item.get(k) == v for k, v in fields.items()):
            raise AuditError(f"{label}: unexpectedly found item matching {fields}")


def require_sorted(items: list[Any], key: str) -> None:
    values = [item.get(key, "") for item in items if isinstance(item, dict)]
    require(values == sorted(values),
            f"items are not sorted by {key}: {values[:5]}")


def require_page(data: dict[str, Any], field: str = "items") -> tuple[list[Any], int | None, dict[str, Any]]:
    require(isinstance(data, dict), "page response is not a dict")
    items = decode_items(data, "list", field)
    total = data.get("total_count")
    page_info = data.get("page_info") or {}
    require(isinstance(total, int), f"total_count is {total!r}, expected int")
    require(isinstance(page_info, dict), f"page_info is {page_info!r}, expected dict")
    return items, total, page_info


def require_no_raw_binary(text: str, label: str) -> None:
    require("\x00" not in text, f"{label}: response contains NUL bytes")
    require("%PDF-" not in text[:200], f"{label}: response contains raw PDF bytes")
    require("\x89PNG" not in text[:200], f"{label}: response contains raw PNG bytes")


def require_no_secret(text: str, secrets: Iterable[str], label: str) -> None:
    for secret in secrets:
        if secret and secret in text:
            raise AuditError(f"{label}: response leaks a credential")


def require_jsonable(data: Any, label: str) -> None:
    try:
        json.dumps(data)
    except (TypeError, ValueError) as exc:
        raise AuditError(f"{label} is not JSON-serializable: {exc}") from exc


def scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(scalar_text(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={scalar_text(v)}" for k, v in value.items())
    return str(value)
