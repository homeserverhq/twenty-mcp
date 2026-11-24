"""SSE-aware MCP JSON-RPC client used by the audit suite.

The audit talks to the same streamable-HTTP endpoint as a real client. It does
not import server code, so it observes real envelopes, TOON strings, and error
text. Twenty returns ``text/event-stream`` for every response, even when the
caller asks for JSON, so SSE parsing is built in.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
from toon_mcp import toon_to_json


class AuditError(AssertionError):
    """Raised when a tool response violates an expectation."""


def token_from_env() -> str:
    for name in ("API_KEY", "TWENTY_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _token_from_env() -> str:
    return token_from_env()


def _parse_sse(body: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    data_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line == "" and data_lines:
            payload = "\n".join(data_lines)
            data_lines = []
            try:
                messages.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
    if data_lines:
        try:
            messages.append(json.loads("\n".join(data_lines)))
        except json.JSONDecodeError:
            pass
    return messages


class ToolCall:
    """One ``tools/call`` result plus convenience decoding."""

    def __init__(self, name: str, arguments: dict[str, Any],
                 result: dict[str, Any] | None, elapsed: float):
        self.name = name
        self.arguments = arguments
        self.result = result or {}
        self.elapsed = elapsed
        self.is_error = bool(self.result.get("isError"))
        content = self.result.get("content") or [{}]
        self.text = content[0].get("text", "") if content else ""
        structured = self.result.get("structuredContent")
        self.data: dict[str, Any] = structured if isinstance(structured, dict) else {}
        if not self.data and self.text:
            try:
                parsed = json.loads(self.text)
                if isinstance(parsed, dict):
                    self.data = parsed
            except Exception:
                pass

    @property
    def error(self) -> str:
        return (self.text or "unknown tool error").strip()

    def items(self, field: str = "items") -> list[Any]:
        return decode_items(self.data, self.name, field)

    def to_check(self) -> dict[str, Any]:
        return {
            "tool": self.name,
            "args": self.arguments,
            "elapsed": round(self.elapsed, 3),
            "is_error": self.is_error,
            "text": self.text[:4000],
            "data": self.data,
        }


def decode_items(data: dict[str, Any], tool: str,
                 field: str = "items") -> list[Any]:
    """Decode an items field, accepting TOON strings and plain lists."""
    if not isinstance(data, dict):
        raise AuditError(f"{tool}: response is {type(data).__name__}, expected dict")
    if field not in data:
        raise AuditError(f"{tool}: response is missing {field!r}: {data!r}")
    raw = data[field]
    if isinstance(raw, str):
        try:
            raw = toon_to_json(raw)
        except Exception as exc:
            raise AuditError(
                f"{tool}: {field} is not valid TOON ({exc}); raw={raw!r}"
            ) from exc
    if not isinstance(raw, list):
        raise AuditError(
            f"{tool}: {field} is {type(raw).__name__}, expected list; raw={raw!r}"
        )
    return raw


class AuditClient:
    """Synchronous MCP JSON-RPC client with SSE and session support."""

    def __init__(self, url: str | None = None, token: str | None = None,
                 timeout: float = 120.0, require_token: bool = True):
        self.url = (
            url
            or os.getenv("MCP_URL")
            or f"http://localhost:{os.getenv('MCP_SERVER_PORT', '80')}/mcp"
        )
        self.token = token if token is not None else _token_from_env()
        if require_token and not self.token:
            raise SystemExit(
                "Set API_KEY (or TWENTY_API_KEY) before running the audit."
            )
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        self.client = httpx.Client(timeout=timeout)
        self._id = 0
        self._session_id = ""
        self._tools: list[dict[str, Any]] | None = None
        self._initialize()

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = dict(self.headers)
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        response = self.client.post(self.url, headers=headers, json=payload)
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self._session_id = session_id
        response.raise_for_status()
        if not response.content:
            return {}
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            messages = _parse_sse(response.text)
            if not messages:
                return {}
            wanted = payload.get("id")
            for message in messages:
                if message.get("id") == wanted:
                    return message
            return messages[0]
        try:
            data = response.json()
        except ValueError:
            return {}
        if isinstance(data, list):
            return data[0] if data else {}
        return data

    def _initialize(self) -> None:
        self._post({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "twenty-audit", "version": "1.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> ToolCall:
        self._id += 1
        started = time.perf_counter()
        data = self._post({
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })
        elapsed = time.perf_counter() - started
        if "error" in data:
            raise AuditError(f"{name}: JSON-RPC error: {data['error']}")
        return ToolCall(name, arguments or {}, data.get("result"), elapsed)

    def tools(self) -> list[dict[str, Any]]:
        if self._tools is None:
            self._id += 1
            data = self._post({
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "tools/list",
                "params": {},
            })
            self._tools = (data.get("result") or {}).get("tools", [])
        return self._tools

    def tool_names(self) -> set[str]:
        return {tool.get("name", "") for tool in self.tools()}

    def close(self) -> None:
        self.client.close()
