"""Error taxonomy and destructive semantics contracts."""

from __future__ import annotations

from ..expect import require
from ..harness import Scenario, scenario

MISSING_UUID = "11111111-1111-4111-8111-111111111111"


@scenario("errors", "not_found_validation_and_delete_twice",
          ["create_company", "get_company_by_id", "update_company",
           "delete_company_by_id", "delete_companies", "update_companies",
           "list_companies"])
def not_found_validation_and_delete_twice(s: Scenario) -> None:
    name = s.fixture("error-company")
    created = s.call("create error fixture", "create_company", {"name": name})
    rid = str(created.data.get("id") or "")
    s.check("error fixture has an id", lambda: require(bool(rid), created.data))
    if not rid:
        return
    s.own(rid)
    s.cleanup("delete_company_by_id", {"id": rid}, "cleanup error fixture")

    s.expect_error("malformed UUID is rejected", "get_company_by_id",
                   {"id": "not-a-uuid"},
                   contains=("400", "uuid", "valid"))
    s.expect_error("valid but unknown UUID reports not found",
                   "get_company_by_id", {"id": MISSING_UUID},
                   contains=("404", "not found"))
    s.expect_error("update with no mutable fields is rejected",
                   "update_company", {"id": rid},
                   contains=("At least one field", "field"))
    s.expect_error("create without a required field is rejected",
                   "create_company", {},
                   contains=("required", "validation", "missing"))

    s.call("delete error fixture", "delete_company_by_id", {"id": rid})
    s.expect_error("second delete reports not found", "delete_company_by_id",
                   {"id": rid}, contains=("404", "not found"))
    s.expect_error("deleted record is not gettable", "get_company_by_id",
                   {"id": rid}, contains=("404", "not found"))
    s.expect_error("deleted record is not updatable", "update_company",
                   {"id": rid, "name": name + "-late"},
                   contains=("404", "not found"))

    deleted_again = s.call("bulk delete an already deleted fixture",
                           "delete_companies", {"ids": [rid]})
    s.check("bulk delete of a missing record reports zero deleted",
            lambda: require(deleted_again.data.get("count") == 0,
                            deleted_again.data))

    s.expect_error("empty bulk delete is rejected", "delete_companies",
                   {"ids": []}, contains=("at least one", "ids"))
    s.expect_error("empty bulk update is rejected", "update_companies",
                   {"ids": [], "name": name}, contains=("at least one", "ids"))
    s.expect_error("limit below one is rejected on a list",
                   "list_companies", {"limit": 0}, contains=("limit",))
    s.expect_error("limit above the maximum is rejected on a list",
                   "list_companies", {"limit": 201}, contains=("limit",))
