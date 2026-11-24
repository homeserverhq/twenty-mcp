"""Workspace-member read and reversible update contracts."""

from __future__ import annotations

from ..expect import require
from ..harness import Scenario, scenario


@scenario("workspace_members", "reversible_profile_update",
          ["list_workspace_members", "get_workspace_member_by_id",
           "update_workspace_member", "update_workspace_members"])
def reversible_profile_update(s: Scenario) -> None:
    listed = s.call("list workspace members", "list_workspace_members",
                    {"limit": 2})
    items = s.items("workspace members decode", listed)
    s.check("workspace member list respects limit",
            lambda: require(len(items) <= 2, f"got {len(items)}"))
    s.check("workspace member list exposes total_count",
            lambda: require(isinstance(listed.data.get("total_count"), int),
                            listed.data))

    targets = sorted(s.run.adapter.allowed_mutation_ids)
    s.check("audit workspace member is configured",
            lambda: require(bool(targets), "no AUDIT_WORKSPACE_MEMBER_ID or email match"))
    if not targets:
        return
    member_id = targets[0]

    full = s.call("get audit workspace member", "get_workspace_member_by_id",
                  {"id": member_id, "include_all_fields": True}).data
    s.check("workspace member get returns the requested record",
            lambda: require(str(full.get("id")) == member_id, full))
    original = str(full.get("colorScheme") or "System")
    alternate = "Dark" if original != "Dark" else "Light"

    s.cleanup("update_workspace_member",
              {"id": member_id, "colorScheme": original},
              "restore workspace member colorScheme")

    s.call("update workspace member colorScheme", "update_workspace_member",
           {"id": member_id, "colorScheme": alternate})
    changed = s.call("get updated workspace member", "get_workspace_member_by_id",
                     {"id": member_id, "include_all_fields": True}).data
    s.check("single workspace-member update is persisted",
            lambda: require(changed.get("colorScheme") == alternate, changed))

    s.call("bulk update workspace member colorScheme",
           "update_workspace_members",
           {"ids": [member_id], "colorScheme": original})
    restored = s.call("get restored workspace member", "get_workspace_member_by_id",
                      {"id": member_id, "include_all_fields": True}).data
    s.check("bulk workspace-member update restores the original",
            lambda: require(restored.get("colorScheme") == original, restored))

    s.expect_error("workspace member update with no fields is rejected",
                   "update_workspace_member", {"id": member_id},
                   contains=("At least one field", "field"))
