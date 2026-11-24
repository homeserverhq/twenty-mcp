"""Workspace-scope and cross-request token isolation contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..expect import require
from ..harness import Scenario, scenario
from ..mcp_client import AuditClient


@scenario("isolation", "concurrent_token_isolation",
          ["list_companies", "create_company", "delete_company_by_id"])
def concurrent_token_isolation(s: Scenario) -> None:
    valid = s.run.client
    invalid = AuditClient(token="not-a-valid-token-for-isolation",
                          require_token=False)
    try:
        def _call(client: AuditClient):
            return client.call("list_companies", {"limit": 1})

        jobs = []
        with ThreadPoolExecutor(max_workers=12) as pool:
            for _ in range(6):
                jobs.append(("valid", pool.submit(_call, valid)))
                jobs.append(("invalid", pool.submit(_call, invalid)))
        valid_ok = 0
        invalid_ok = 0
        invalid_errors: list[str] = []
        for label, future in jobs:
            call = future.result()
            if label == "valid":
                if not call.is_error:
                    valid_ok += 1
            else:
                if call.is_error:
                    invalid_ok += 1
                    invalid_errors.append(call.text)
        s.check("valid token calls succeed under concurrency",
                lambda: require(valid_ok == 6, f"{valid_ok}/6 succeeded"))
        s.check("invalid token calls fail under concurrency",
                lambda: require(invalid_ok == 6, f"{invalid_ok}/6 rejected"))
        s.check("invalid-token errors never contain the valid token",
                lambda: require(
                    all(valid.token not in text for text in invalid_errors),
                    "valid token appeared in an invalid-token error",
                ))
    finally:
        invalid.close()

    secondary = s.run.clients.get("secondary")
    if secondary is None:
        s.skip("same-workspace visibility across two keys",
               "no AUDIT_SECONDARY_API_KEY configured; API key is workspace-scoped")
        return
    name = s.fixture("isolation-company")
    created = s.call("create isolation fixture", "create_company", {"name": name})
    rid = str(created.data.get("id") or "")
    if rid:
        s.own(rid)
        s.cleanup("delete_company_by_id", {"id": rid}, "cleanup isolation fixture")
        visible = secondary.call("get_company_by_id",
                                 {"id": rid, "include_all_fields": True})
        s.check("second key sees a record in the same workspace",
                lambda: require(not visible.is_error, visible.text[:300]))
