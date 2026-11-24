"""Field-projection contracts, including the intentional aggregate gate."""

from __future__ import annotations

import os

from ..expect import require
from ..harness import Scenario, scenario
from .resources import _find_in_pages


@scenario("projection", "single_and_aggregate_projection",
          ["get_company_by_id", "list_companies", "create_company",
           "update_company", "get_note_by_id", "list_notes", "create_note"])
def single_and_aggregate_projection(s: Scenario) -> None:
    gate = os.getenv("ALLOW_ALL_AGGREGATE", "false").lower() in ("1", "true", "yes")
    name = s.fixture("projection")
    created = s.call("create projection company", "create_company", {"name": name})
    rid = str(created.data.get("id") or "")
    s.check("projection fixture has an id", lambda: require(bool(rid), created.data))
    if not rid:
        return
    s.own(rid)
    s.cleanup("delete_company_by_id", {"id": rid}, "cleanup projection company")

    default = s.call("get company default projection", "get_company_by_id",
                     {"id": rid}).data
    full = s.call("get company full projection", "get_company_by_id",
                  {"id": rid, "include_all_fields": True}).data
    s.check("single-record get honors include_all_fields",
            lambda: require(
                "createdAt" in full and "createdAt" not in default,
                f"default={sorted(default)} full={sorted(full)}",
            ))
    s.check("full single-record projection keeps the id and name",
            lambda: require(
                full.get("id") == rid and full.get("name") == name,
                full,
            ))

    default_list = _find_in_pages(s, "list_companies", rid)
    default_item = next((item for item in default_list if item.get("id") == rid), {})
    full_list = _find_in_pages(s, "list_companies", rid,
                               extra={"include_all_fields": True})
    full_item = next((item for item in full_list if item.get("id") == rid), {})
    s.check("aggregate list returns the fixture",
            lambda: require(bool(default_item) and bool(full_item),
                            f"default={bool(default_item)} full={bool(full_item)}"))
    if gate:
        s.check("aggregate list honors include_all_fields when enabled",
                lambda: require(
                    "createdAt" in full_item and "createdAt" not in default_item,
                    f"default={sorted(default_item)} full={sorted(full_item)}",
                ))
    else:
        s.check("aggregate list intentionally ignores include_all_fields when disabled",
                lambda: require(
                    set(full_item) == set(default_item)
                    and "createdAt" not in full_item,
                    f"default={sorted(default_item)} full={sorted(full_item)}",
                ))

    create_keys = set(created.data)
    update_call = s.call("update projection company", "update_company",
                         {"id": rid, "name": name + "-updated"})
    update_keys = set(update_call.data)
    if gate:
        s.check("create and update responses include full fields when enabled",
                lambda: require(
                    "createdAt" in create_keys and "createdAt" in update_keys,
                    f"create={sorted(create_keys)} update={sorted(update_keys)}",
                ))
    else:
        s.check("create and update responses stay bounded when the gate is disabled",
                lambda: require(
                    "createdAt" not in create_keys and "createdAt" not in update_keys,
                    f"create={sorted(create_keys)} update={sorted(update_keys)}",
                ))

    note_name = s.fixture("projection-note")
    note = s.call("create projection note", "create_note",
                  {"title": note_name, "markdown": "projection body"})
    nid = str(note.data.get("id") or "")
    if nid:
        s.own(nid)
        s.cleanup("delete_note_by_id", {"id": nid}, "cleanup projection note")
        note_full = s.call("get note full projection", "get_note_by_id",
                           {"id": nid, "include_all_fields": True}).data
        body = note_full.get("bodyV2") or {}
        s.check("bodyV2 is reduced to rendered markdown",
                lambda: require(
                    isinstance(body, dict)
                    and "markdown" in body
                    and "blocknote" not in body,
                    body,
                ))
        listed = _find_in_pages(s, "list_notes", nid)
        listed_note = next((item for item in listed if item.get("id") == nid), {})
        s.check("aggregate note list also reduces bodyV2 to markdown",
                lambda: require(
                    isinstance(listed_note.get("bodyV2"), dict)
                    and "markdown" in listed_note.get("bodyV2", {})
                    and "blocknote" not in listed_note.get("bodyV2", {}),
                    listed_note.get("bodyV2"),
                ))
