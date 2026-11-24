"""Cursor pagination and silent-truncation contracts."""

from __future__ import annotations

from ..expect import require
from ..harness import Scenario, scenario

BULK = 61


@scenario("pagination", "list_cursor_and_total",
          ["list_companies", "create_company", "delete_companies"])
def list_cursor_and_total(s: Scenario) -> None:
    baseline_call = s.call("baseline list_companies", "list_companies",
                           {"limit": 1})
    baseline = baseline_call.data.get("total_count")
    s.check("baseline list exposes total_count",
            lambda: require(isinstance(baseline, int), baseline_call.data))

    ids: list[str] = []
    for index in range(BULK):
        name = s.fixture(f"page-{index:03d}")
        call = s.call(f"create pagination company {index}", "create_company",
                      {"name": name})
        record_id = str(call.data.get("id") or "")
        if record_id:
            s.own(record_id)
            ids.append(record_id)
    s.check("created the pagination fixture set",
            lambda: require(len(ids) == BULK, f"created {len(ids)} of {BULK}"))
    if ids:
        s.cleanup("delete_companies", {"ids": ids}, "cleanup pagination companies")

    expected_total = (baseline if isinstance(baseline, int) else 0) + len(ids)
    first_call, first, total, page_info = s.page(
        "first bounded page", "list_companies", {"limit": 2}
    )
    s.check("bounded list respects limit",
            lambda: require(len(first) <= 2, f"got {len(first)}"))
    s.check("total_count includes every record, not just the page",
            lambda: require(total == expected_total,
                            f"total_count={total}, expected {expected_total}"))
    s.check("first page reports another page",
            lambda: require(bool(page_info.get("hasNextPage")), page_info))
    cursor = page_info.get("endCursor")
    s.check("first page exposes an end cursor",
            lambda: require(bool(cursor), page_info))

    if cursor:
        _, second, total2, page_info2 = s.page(
            "second bounded page", "list_companies",
            {"limit": 2, "starting_after": cursor},
        )
        first_ids = {str(item.get("id")) for item in first}
        second_ids = {str(item.get("id")) for item in second}
        s.check("cursor advances without duplicates",
                lambda: require(not (first_ids & second_ids),
                                f"overlap={sorted(first_ids & second_ids)}"))
        s.check("cursor keeps the same total_count",
                lambda: require(total2 == expected_total,
                                f"total_count={total2}, expected {expected_total}"))
        s.check("second page returns items",
                lambda: require(bool(second), "second page is empty"))

    s.expect_error("limit below one is rejected", "list_companies",
                   {"limit": 0}, contains=("limit",))
    s.expect_error("limit above the backend maximum is rejected",
                   "list_companies", {"limit": 201}, contains=("limit",))

    if ids:
        deleted = s.call("bulk delete pagination companies", "delete_companies",
                         {"ids": ids})
        s.check("bulk delete reports every fixture deletion",
                lambda: require(deleted.data.get("count") == len(ids), deleted.data))
        final = s.call("final list_companies", "list_companies", {"limit": 1})
        s.check("record count returns to baseline",
                lambda: require(final.data.get("total_count") == baseline,
                                f"total_count={final.data.get('total_count')}, "
                                f"baseline={baseline}"))
