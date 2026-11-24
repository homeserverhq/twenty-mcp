"""Status, auth, and schema-only availability contracts."""

from __future__ import annotations

from ..expect import require
from ..harness import Scenario, scenario
from ..mcp_client import AuditClient


@scenario("status", "health_and_auth",
          ["check_server_status", "list_companies"])
def health_and_auth(s: Scenario) -> None:
    status = s.call("check_server_status", "check_server_status").data
    s.check("valid credentials report connected",
            lambda: require(status.get("status") == "connected", status))
    s.check("valid credentials report the backend status",
            lambda: require(status.get("backend_response") == 200, status))

    anonymous = AuditClient(token="", require_token=False)
    try:
        anon_status = anonymous.call("check_server_status", {}).data
        s.check("missing credentials are not reported as connected",
                lambda: require(anon_status.get("status") != "connected",
                                anon_status))
        anon_call = anonymous.call("list_companies", {"limit": 1})
        s.check("missing credentials are rejected on a data call",
                lambda: require(anon_call.is_error, anon_call.text[:300]))
    finally:
        anonymous.close()

    invalid = AuditClient(token="not-a-valid-twenty-api-key", require_token=False)
    try:
        invalid_status = invalid.call("check_server_status", {}).data
        s.check("invalid credentials are not reported as connected",
                lambda: require(invalid_status.get("status") != "connected",
                                invalid_status))
        invalid_call = invalid.call("list_companies", {"limit": 1})
        s.check("invalid credentials are rejected on a data call",
                lambda: require(invalid_call.is_error, invalid_call.text[:300]))
        s.check("invalid-token error does not leak the valid token",
                lambda: require(
                    s.run.client.token not in invalid_call.text,
                    "valid token appears in the error text",
                ))
    finally:
        invalid.close()

    tools = s.run.client.tools()
    s.check("tools/list is available without a data mutation",
            lambda: require(len(tools) == 115, f"got {len(tools)} tools"))
