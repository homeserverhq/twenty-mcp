"""L0 schema and metadata contract."""

from __future__ import annotations

import re
from typing import Any

from ..harness import Scenario, scenario

SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
DATE_PARAM = re.compile(r"(At$|Date$|_at$|_date$)")
ISO_HINT = "ISO 8601 format (2026-06-22T15:00:00-04:00)."


def _collect(s: Scenario, label: str, fn) -> None:
    tools = s.run.client.tools()
    failures: list[str] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        try:
            fn(name, tool)
        except Exception as exc:
            failures.append(f"{name}: {exc}")
    s.check(label, lambda: _require_no_failures(failures))


def _require_no_failures(failures: list[str]) -> None:
    if failures:
        raise AssertionError("; ".join(failures[:25]))


@scenario("schema", "tool_metadata", [])
def tool_metadata(s: Scenario) -> None:
    tools = s.run.client.tools()
    s.check("tools/list returns 115 tools",
            lambda: _require_eq(len(tools), 115, "tool count"))
    s.check("tool names are unique",
            lambda: _require_eq(len({t.get("name") for t in tools}), len(tools),
                               "unique tool names"))

    _collect(s, "tool names are snake_case", lambda name, tool: _snake(name))
    _collect(s, "tool descriptions are present", lambda name, tool: _desc(tool))
    _collect(s, "input schemas are objects", lambda name, tool: _schema(tool))
    _collect(s, "parameters have descriptions", lambda name, tool: _prop_desc(tool))
    _collect(s, "annotations are complete", lambda name, tool: _annotations(tool))
    _collect(s, "read-only and destructive hints do not conflict",
             lambda name, tool: _not_both(tool))
    _collect(s, "delete tools are destructive and not read-only",
             lambda name, tool: _delete_annotations(name, tool))
    _collect(s, "delete tools do not claim idempotence",
             lambda name, tool: _delete_idempotence(name, tool))
    _collect(s, "date parameters carry the canonical ISO hint",
             lambda name, tool: _date_hints(tool))
    _collect(s, "list tools expose limit and cursor",
             lambda name, tool: _pagination_schema(name, tool))
    _collect(s, "aggregate list docstrings describe the projection gate",
             lambda name, tool: _projection_doc(name, tool))
    _collect(s, "update tools require an id",
             lambda name, tool: _update_id(name, tool))


def _require_eq(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")


def _snake(name: str) -> None:
    if not SNAKE.match(name):
        raise AssertionError("not snake_case")


def _desc(tool: dict[str, Any]) -> None:
    desc = str(tool.get("description") or "").strip()
    if not desc or "TODO" in desc.upper():
        raise AssertionError("missing or placeholder description")


def _schema(tool: dict[str, Any]) -> None:
    schema = tool.get("inputSchema") or {}
    if schema.get("type") not in (None, "object"):
        raise AssertionError(f"inputSchema type is {schema.get('type')!r}")
    if not isinstance(schema.get("properties") or {}, dict):
        raise AssertionError("inputSchema.properties is not an object")
    required = schema.get("required") or []
    for prop in required:
        if prop not in (schema.get("properties") or {}):
            raise AssertionError(f"required property {prop!r} is not declared")


def _prop_desc(tool: dict[str, Any]) -> None:
    props = (tool.get("inputSchema") or {}).get("properties") or {}
    for prop, spec in props.items():
        if not isinstance(spec, dict) or not spec.get("description"):
            raise AssertionError(f"parameter {prop!r} has no description")


def _annotations(tool: dict[str, Any]) -> None:
    annotations = tool.get("annotations") or {}
    for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
        if key not in annotations:
            raise AssertionError(f"missing {key}")


def _not_both(tool: dict[str, Any]) -> None:
    annotations = tool.get("annotations") or {}
    if annotations.get("readOnlyHint") and annotations.get("destructiveHint"):
        raise AssertionError("both readOnlyHint and destructiveHint are true")


def _delete_annotations(name: str, tool: dict[str, Any]) -> None:
    if not name.startswith("delete_"):
        return
    annotations = tool.get("annotations") or {}
    if annotations.get("readOnlyHint"):
        raise AssertionError("destructive tool is marked read-only")
    if not annotations.get("destructiveHint"):
        raise AssertionError("delete tool is not marked destructive")


def _delete_idempotence(name: str, tool: dict[str, Any]) -> None:
    if not name.startswith("delete_"):
        return
    annotations = tool.get("annotations") or {}
    if annotations.get("idempotentHint"):
        raise AssertionError("delete tool claims idempotence; repeat delete returns 404")


def _date_hints(tool: dict[str, Any]) -> None:
    props = (tool.get("inputSchema") or {}).get("properties") or {}
    for prop, spec in props.items():
        if not DATE_PARAM.search(prop):
            continue
        description = str((spec or {}).get("description") or "")
        if ISO_HINT not in description:
            raise AssertionError(f"date parameter {prop!r} lacks the ISO hint")


def _pagination_schema(name: str, tool: dict[str, Any]) -> None:
    if not name.startswith("list_"):
        return
    props = (tool.get("inputSchema") or {}).get("properties") or {}
    for prop in ("limit", "starting_after"):
        if prop not in props:
            raise AssertionError(f"missing {prop!r}")


def _projection_doc(name: str, tool: dict[str, Any]) -> None:
    if not name.startswith("list_"):
        return
    props = (tool.get("inputSchema") or {}).get("properties") or {}
    description = str((props.get("include_all_fields") or {}).get("description") or "")
    if "ALLOW_ALL_AGGREGATE" not in description:
        raise AssertionError("include_all_fields does not document the aggregate gate")


def _update_id(name: str, tool: dict[str, Any]) -> None:
    if not name.startswith("update_"):
        return
    schema = tool.get("inputSchema") or {}
    required = schema.get("required") or []
    props = schema.get("properties") or {}
    key = "ids" if "ids" in props else "id"
    if key not in required:
        raise AssertionError(f"missing required {key!r}")
