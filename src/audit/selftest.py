"""Small self-tests for the audit harness and date handling.

Run with ``python -m src.audit.selftest``.
"""

from __future__ import annotations

import json

from toon_mcp import json_to_toon

from src.client import _normalize_datetime

from .expect import require_iso, require_utc
from .mcp_client import _parse_sse, decode_items


def test_sse() -> None:
    body = (
        'event: message\n'
        'data: {"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n\n'
    )
    messages = _parse_sse(body)
    assert messages and messages[0]["id"] == 1
    assert messages[0]["result"]["tools"] == []


def test_toon_decode() -> None:
    items = [{"id": "1", "name": "fixture"}]
    encoded = json_to_toon(items)
    decoded = decode_items({"items": encoded}, "list_fixture")
    assert decoded == items
    assert decode_items({"items": []}, "list_fixture") == []


def test_iso() -> None:
    assert require_iso("2026-11-25T19:00:00.000Z", "dueAt")
    assert require_utc("2026-11-25T19:00:00.000Z", "dueAt")
    assert require_iso("2026-11-25T15:00:00-04:00", "dueAt")
    try:
        require_iso("2026-11-25T15:00:00", "dueAt")
    except AssertionError:
        pass
    else:
        raise AssertionError("naive datetime was accepted")


def test_normalize() -> None:
    assert _normalize_datetime("2026-11-25T15:00:00-04:00") == \
        "2026-11-25T19:00:00.000Z"
    assert _normalize_datetime("2026-11-25T19:00:00Z") == \
        "2026-11-25T19:00:00.000Z"
    assert _normalize_datetime("2026-11-25T19:00:00.123Z") == \
        "2026-11-25T19:00:00.123Z"
    for bad in ("2026-11-25T19:00:00", "2026-11-25", "1795638600"):
        try:
            _normalize_datetime(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid datetime accepted: {bad}")


def main() -> int:
    tests = [test_sse, test_toon_decode, test_iso, test_normalize]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} self-tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
