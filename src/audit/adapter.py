"""Twenty-specific adapter for the generic audit harness."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import yaml

from .backend import RESOURCES, TwentyBackend
from .mcp_client import AuditClient


def _decode_jwt(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


class TwentyAdapter:
    name = "twenty"
    allow_destructive = True

    def __init__(self, token: str):
        self.token = token
        self.manifest = yaml.safe_load(
            Path(__file__).with_name("manifest.yaml").read_text(encoding="utf-8")
        )
        self.backend = TwentyBackend(token=token) if token else None
        self.identity = _decode_jwt(token) if token else {}
        self.aggregate_flag = os.getenv("ALLOW_ALL_AGGREGATE", "false").lower() in (
            "1", "true", "yes",
        )
        self.allowed_mutation_ids: set[str] = set()
        self.protected_ids: dict[str, set[str]] = {}
        self.snapshot: dict[str, Any] = {}
        self.warnings: list[str] = []

    # -- adapter interface -------------------------------------------------

    def fixture_name(self, run_id: str, domain: str, scenario: str,
                     suffix: str = "") -> str:
        value = f"MCPAudit-{run_id}-{domain}-{scenario}"
        if suffix:
            value = f"{value}-{suffix}"
        return value[:200]

    def is_protected(self, name: str) -> bool:
        return False

    def preflight(self, client: AuditClient, full: bool = True) -> list[str]:
        if full:
            self.snapshot = self.backend.snapshot()
            self.protected_ids = {
                resource: set(ids)
                for resource, ids in self.snapshot.get("ids", {}).items()
            }
            self.allowed_mutation_ids = self._find_audit_member()
        if not self.aggregate_flag:
            self.warnings.append(
                "ALLOW_ALL_AGGREGATE=false: aggregate list calls intentionally "
                "ignore include_all_fields; projection contracts assert that "
                "documented behavior."
            )
        if len(self.identity.get("workspaceId", "")) == 0:
            self.warnings.append("Could not decode workspaceId from the API key.")
        self.warnings.append(
            "API key is workspace-scoped; cross-workspace isolation is not "
            "testable against a single workspace."
        )
        return list(self.warnings)

    def residue(self, client: AuditClient, run_id: str) -> dict[str, Any]:
        prefix = f"MCPAudit-{run_id}"
        found = self.backend.residue(prefix)
        post = self.backend.snapshot()
        before = self.snapshot.get("counts", {})
        after = post.get("counts", {})
        side_effect_resources = {"timelineActivity"}
        diffs = {
            resource: {"before": before.get(resource), "after": after.get(resource)}
            for resource in RESOURCES
            if resource not in side_effect_resources
            and before.get(resource) != after.get(resource)
        }
        side_effects = {
            resource: {"before": before.get(resource), "after": after.get(resource)}
            for resource in side_effect_resources
            if before.get(resource) != after.get(resource)
        }
        soft_before = self.snapshot.get("soft_deleted", {})
        soft_after = post.get("soft_deleted", {})
        soft_diffs = {
            resource: {"before": soft_before.get(resource), "after": soft_after.get(resource)}
            for resource in RESOURCES
            if soft_before.get(resource) != soft_after.get(resource)
        }
        return {
            "prefix": prefix,
            "counts": found.get("counts", {}),
            "errors": found.get("errors", {}),
            "count_diffs": diffs,
            "soft_deleted_diffs": soft_diffs,
            "side_effects": side_effects,
        }

    def capabilities(self) -> dict[str, Any]:
        return dict(self.manifest.get("capabilities", {}))

    # -- helpers -----------------------------------------------------------

    def _find_audit_member(self) -> set[str]:
        wanted = os.getenv(
            "AUDIT_WORKSPACE_MEMBER_EMAIL",
            "shbadmin_twenty@selfhostingbox.com",
        ).strip().lower()
        explicit = os.getenv("AUDIT_WORKSPACE_MEMBER_ID", "").strip()
        if explicit:
            return {explicit}
        try:
            members = self.backend.list_all("workspaceMember")
        except Exception as exc:
            self.warnings.append(f"Could not list workspace members: {exc}")
            return set()
        for member in members:
            if str(member.get("userEmail", "")).strip().lower() == wanted and member.get("id"):
                return {str(member["id"])}
        self.warnings.append(
            f"Audit workspace member {wanted!r} not found; workspace-member "
            "updates will be skipped."
        )
        return set()

    def workspace_member(self) -> dict[str, Any] | None:
        for record_id in self.allowed_mutation_ids:
            try:
                return self.backend.get_by_id("workspaceMember", record_id)
            except Exception:
                pass
        return None

    def close(self) -> None:
        if self.backend is not None:
            self.backend.close()
