"""Direct Twenty REST client used for truth checks, snapshots, and residue.

The audit's MCP client observes what a consumer sees. This backend client is
used only for independent verification: total counts, protected-ID snapshots,
soft-deleted counts, and fixture-prefix residue.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

RESOURCES: dict[str, dict[str, Any]] = {
    "company": {"path": "companies", "plural": "companies", "name": "name"},
    "person": {"path": "people", "plural": "people", "name": "name.firstName"},
    "opportunity": {"path": "opportunities", "plural": "opportunities", "name": "name"},
    "note": {"path": "notes", "plural": "notes", "name": "title"},
    "task": {"path": "tasks", "plural": "tasks", "name": "title"},
    "workflow": {"path": "workflows", "plural": "workflows", "name": "name"},
    "workspaceMember": {"path": "workspaceMembers", "plural": "workspaceMembers", "name": "userEmail"},
    "attachment": {"path": "attachments", "plural": "attachments", "name": "name"},
    "noteTarget": {"path": "noteTargets", "plural": "noteTargets", "name": None},
    "taskTarget": {"path": "taskTargets", "plural": "taskTargets", "name": None},
    "timelineActivity": {"path": "timelineActivities", "plural": "timelineActivities", "name": "name"},
    "calendarEvent": {"path": "calendarEvents", "plural": "calendarEvents", "name": "title"},
    "calendarEventParticipant": {
        "path": "calendarEventParticipants",
        "plural": "calendarEventParticipants",
        "name": "displayName",
    },
    "message": {"path": "messages", "plural": "messages", "name": "subject"},
    "messageThread": {"path": "messageThreads", "plural": "messageThreads", "name": "subject"},
    "messageParticipant": {
        "path": "messageParticipants",
        "plural": "messageParticipants",
        "name": "displayName",
    },
    "callRecording": {"path": "callRecordings", "plural": "callRecordings", "name": "title"},
}


class TwentyBackend:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or os.getenv("TWENTY_BASE_URL", "")).rstrip("/")
        self.token = token or os.getenv("API_KEY", "") or os.getenv("TWENTY_API_KEY", "")
        if not self.base_url:
            raise SystemExit("Set TWENTY_BASE_URL before running the audit.")
        if not self.token:
            raise SystemExit("Set API_KEY (or TWENTY_API_KEY) before running the audit.")
        self.client = httpx.Client(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = None
        for _ in range(5):
            response = self.client.get(
                f"{self.base_url}{path}", params=params or {}
            )
            if response.status_code != 429:
                break
            try:
                retry_after = float(response.headers.get("retry-after", "10"))
            except (TypeError, ValueError):
                retry_after = 10.0
            time.sleep(max(1.0, min(retry_after, 60.0)))
        if response is None:
            raise RuntimeError(f"GET {path} produced no response")
        if response.status_code >= 400:
            raise RuntimeError(
                f"GET {path} failed: {response.status_code} {response.text[:300]}"
            )
        return response.json()

    def list_page(self, resource: str, limit: int = 200,
                  starting_after: str | None = None,
                  filter: str | None = None) -> dict[str, Any]:
        spec = RESOURCES[resource]
        params: dict[str, Any] = {"limit": limit}
        if starting_after:
            params["starting_after"] = starting_after
        if filter:
            params["filter"] = filter
        raw = self._get(f"/rest/{spec['path']}", params)
        return {
            "items": raw.get("data", {}).get(spec["plural"], []),
            "total_count": raw.get("totalCount"),
            "page_info": raw.get("pageInfo") or {},
        }

    def list_all(self, resource: str,
                 filter: str | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(50):
            page = self.list_page(resource, 200, cursor, filter)
            items.extend(page["items"])
            page_info = page["page_info"]
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break
        return items

    def ids(self, resource: str) -> set[str]:
        return {
            str(item.get("id"))
            for item in self.list_all(resource)
            if item.get("id")
        }

    def count(self, resource: str, filter: str | None = None) -> int:
        page = self.list_page(resource, 1, None, filter)
        value = page.get("total_count")
        if not isinstance(value, int):
            raise RuntimeError(f"{resource}: totalCount missing from response")
        return value

    def soft_deleted_count(self, resource: str) -> int:
        return self.count(resource, "deletedAt[is]:NOT_NULL")

    def get_by_id(self, resource: str, record_id: str) -> dict[str, Any] | None:
        spec = RESOURCES[resource]
        response = self.client.get(f"{self.base_url}/rest/{spec['path']}/{record_id}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise RuntimeError(
                f"GET {resource}/{record_id} failed: "
                f"{response.status_code} {response.text[:200]}"
            )
        raw = response.json()
        data = raw.get("data", {})
        key = resource[0].lower() + resource[1:]
        return data.get(key) or (next(iter(data.values())) if data else None)

    def snapshot(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        soft_deleted: dict[str, int] = {}
        ids: dict[str, list[str]] = {}
        for resource in RESOURCES:
            counts[resource] = self.count(resource)
            try:
                soft_deleted[resource] = self.soft_deleted_count(resource)
            except Exception:
                soft_deleted[resource] = -1
            ids[resource] = sorted(self.ids(resource))
        return {
            "counts": counts,
            "soft_deleted": soft_deleted,
            "ids": ids,
        }

    def residue(self, prefix: str) -> dict[str, Any]:
        found: dict[str, int] = {}
        errors: dict[str, str] = {}
        for resource, spec in RESOURCES.items():
            field = spec.get("name")
            if not field:
                continue
            filter_value = f'{field}[ilike]:"%{prefix}%"'
            try:
                found[resource] = self.count(resource, filter_value)
            except Exception as exc:
                errors[resource] = str(exc)[:200]
        return {"counts": found, "errors": errors}

    def close(self) -> None:
        self.client.close()
