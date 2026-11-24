"""Scenario and result plumbing for the Twenty MCP audit suite.

Safety rule: every destructive or mutating call must target an ID that this run
created (or an explicitly allowed reversible target such as the audit user's
own workspace member). ``protected_names`` alone cannot protect real UUIDs.
"""

from __future__ import annotations

import re
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .expect import require_page
from .mcp_client import AuditClient, AuditError, ToolCall

REGISTRY: list["ScenarioDef"] = []
MUTATING_TOOL = re.compile(r"^(delete_|update_)")


@dataclass
class ScenarioDef:
    domain: str
    name: str
    tools: tuple[str, ...]
    fn: Callable[["Scenario"], None]


def scenario(domain: str, name: str, tools: list[str] | tuple[str, ...]):
    def decorator(fn: Callable[["Scenario"], None]):
        REGISTRY.append(ScenarioDef(domain, name, tuple(tools), fn))
        return fn

    return decorator


@dataclass
class Result:
    domain: str
    scenario: str
    label: str
    tool: str
    status: str
    detail: str = ""
    elapsed: float = 0.0
    args: dict[str, Any] = field(default_factory=dict)


class Run:
    def __init__(self, clients: dict[str, AuditClient], adapter: Any,
                 domains: set[str] | None = None):
        self.clients = clients
        self.adapter = adapter
        self.domains = domains
        self.run_id = uuid.uuid4().hex[:8]
        self.results: list[Result] = []
        self.failures = 0
        self.skips = 0
        self.tools_called: set[str] = set()
        self.declared_tools: set[str] = set()
        self.owned_ids: set[str] = set()
        self.allowed_mutation_ids: set[str] = set(adapter.allowed_mutation_ids)
        self.warnings: list[str] = []

    @property
    def client(self) -> AuditClient:
        return self.clients["primary"]

    def record(self, domain: str, scenario_name: str, label: str,
               tool: str, status: str, detail: str = "", elapsed: float = 0.0,
               args: dict[str, Any] | None = None) -> None:
        self.results.append(Result(
            domain=domain, scenario=scenario_name, label=label, tool=tool,
            status=status, detail=detail, elapsed=elapsed, args=args or {},
        ))
        if status == "FAIL":
            self.failures += 1
        elif status == "SKIP":
            self.skips += 1

    def scenarios(self) -> list[ScenarioDef]:
        selected = [
            sc for sc in REGISTRY
            if self.domains is None or sc.domain in self.domains
        ]
        order: dict[str, int] = {}
        for index, sc in enumerate(REGISTRY):
            order.setdefault(sc.domain, index)
        selected.sort(key=lambda sc: (order.get(sc.domain, 0), sc.name))
        return selected

    def run(self) -> None:
        for definition in self.scenarios():
            self.declared_tools.update(definition.tools)
            scenario = Scenario(self, definition)
            try:
                with scenario:
                    definition.fn(scenario)
            except Exception as exc:
                self.record(
                    definition.domain, definition.name, "scenario aborted",
                    "", "FAIL",
                    f"{type(exc).__name__}: {exc}\n"
                    f"{traceback.format_exc(limit=4)}",
                )

    def own(self, record_id: Any) -> str:
        value = str(record_id)
        if value:
            self.owned_ids.add(value)
        return value


class Scenario:
    def __init__(self, run: Run, definition: ScenarioDef):
        self.run = run
        self.definition = definition
        safe = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{definition.domain}-{definition.name}")
        self.prefix = f"MCPAudit-{run.run_id}-{safe}"
        self.cleanups: list[tuple[str, dict[str, Any], str]] = []
        self.failed = False

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "Scenario":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._run_cleanups()
        return False

    def _record(self, label: str, tool: str, status: str,
                detail: str = "", elapsed: float = 0.0,
                args: dict[str, Any] | None = None) -> None:
        if status == "FAIL":
            self.failed = True
        self.run.record(
            self.definition.domain, self.definition.name, label, tool,
            status, detail, elapsed, args,
        )

    # -- fixture helpers ---------------------------------------------------

    def fixture(self, suffix: str = "") -> str:
        value = f"{self.prefix}-{suffix}" if suffix else self.prefix
        return value[:200]

    def own(self, record_id: Any) -> str:
        return self.run.own(record_id)

    def allow_mutation(self, record_id: Any) -> None:
        self.run.allowed_mutation_ids.add(str(record_id))

    def _guard(self, tool: str, args: dict[str, Any]) -> None:
        if not MUTATING_TOOL.match(tool):
            return
        targets: list[str] = []
        for key in ("id", "ids"):
            value = args.get(key)
            if isinstance(value, str):
                targets.append(value)
            elif isinstance(value, list):
                targets.extend(str(item) for item in value)
        for target in targets:
            if target in self.run.owned_ids:
                continue
            if target in self.run.allowed_mutation_ids:
                continue
            raise AuditError(
                f"{tool}: refusing to mutate {target!r}; it was not created by "
                f"this audit run. Owned IDs: {len(self.run.owned_ids)}."
            )

    # -- calls -------------------------------------------------------------

    def call(self, label: str, tool: str, args: dict[str, Any] | None = None,
             required: bool = True, account: str = "primary") -> ToolCall:
        args = args or {}
        self._guard(tool, args)
        client = self.run.clients.get(account)
        if client is None:
            raise AuditError(f"no client for account {account!r}")
        call = client.call(tool, args)
        self.run.tools_called.add(tool)
        if call.is_error:
            self._record(label, tool, "FAIL", call.error, call.elapsed, args)
            if required:
                raise AuditError(f"{tool}: {call.error}")
        else:
            self._record(label, tool, "PASS", "", call.elapsed, args)
        return call

    def call_any(self, label: str, tool: str,
                 args: dict[str, Any] | None = None,
                 account: str = "primary") -> ToolCall:
        return self.call(label, tool, args, required=False, account=account)

    def expect_error(self, label: str, tool: str,
                     args: dict[str, Any] | None = None,
                     contains: tuple[str, ...] = ("404", "not found",
                                                  "does not exist"),
                     account: str = "primary") -> ToolCall:
        args = args or {}
        self._guard(tool, args)
        call = self.run.clients[account].call(tool, args)
        self.run.tools_called.add(tool)
        lowered = call.error.lower()
        needles = tuple(needle.lower() for needle in contains)
        ok = call.is_error and any(needle in lowered for needle in needles)
        self._record(
            label, tool, "PASS" if ok else "FAIL",
            "" if ok else call.error, call.elapsed, args,
        )
        return call

    def attempt(self, label: str, tool: str,
                args: dict[str, Any] | None = None) -> ToolCall:
        call = self.run.client.call(tool, args)
        self.run.tools_called.add(tool)
        self._record(
            label, tool, "PASS" if not call.is_error else "SKIP",
            "" if not call.is_error else call.error, call.elapsed, args,
        )
        return call

    # -- checks ------------------------------------------------------------

    def check(self, label: str, fn: Callable[[], Any],
              tool: str = "assert") -> Any:
        try:
            value = fn()
        except Exception as exc:
            self._record(label, tool, "FAIL", str(exc))
            return None
        self._record(label, tool, "PASS")
        return value

    def require(self, label: str, condition: Any, detail: str = "") -> bool:
        def _check() -> bool:
            if not condition:
                raise AuditError(detail or f"condition failed: {label}")
            return True

        return bool(self.check(label, _check))

    def items(self, label: str, call: ToolCall,
              field: str = "items") -> list[Any]:
        holder: dict[str, list[Any]] = {}

        def _decode():
            holder["items"] = call.items(field)
            return holder["items"]

        self.check(label, _decode, tool=call.name)
        return holder.get("items", [])

    def page(self, label: str, tool: str, args: dict[str, Any] | None = None,
             account: str = "primary") -> tuple[ToolCall, list[Any], int | None, dict[str, Any]]:
        call = self.call(label, tool, args, account=account)
        holder: dict[str, Any] = {"items": [], "total": None, "page_info": {}}

        def _decode():
            items, total, page_info = require_page(call.data)
            holder.update(items=items, total=total, page_info=page_info)

        self.check(f"{label} page shape", _decode, tool=tool)
        return call, holder["items"], holder["total"], holder["page_info"]

    def skip(self, label: str, reason: str) -> None:
        self._record(label, "", "SKIP", reason)

    # -- cleanup -----------------------------------------------------------

    def cleanup(self, tool: str, args: dict[str, Any],
                label: str | None = None) -> None:
        self.cleanups.append((tool, dict(args), label or f"cleanup {tool}"))

    def _run_cleanups(self) -> None:
        for tool, args, label in reversed(self.cleanups):
            try:
                call = self.run.clients["primary"].call(tool, args)
            except Exception as exc:
                self._record(label, tool, "WARN", f"cleanup raised: {exc}")
                continue
            if call.is_error:
                lowered = call.error.lower()
                benign = any(
                    phrase in lowered
                    for phrase in ("not found", "does not exist", "404",
                                   "forbidden", "403", "no such")
                )
                self._record(label, tool, "PASS" if benign else "WARN",
                             call.error)
            else:
                self._record(label, tool, "PASS")
