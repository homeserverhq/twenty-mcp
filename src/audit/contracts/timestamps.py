"""ISO 8601 input/output and instant-preservation contracts."""

from __future__ import annotations

import datetime as dt

from ..expect import require, require_instant, require_iso, require_utc
from ..harness import Scenario, scenario

OFFSET = "2026-11-25T15:00:00-04:00"
OFFSET_UTC = dt.datetime(2026, 11, 25, 19, 0, tzinfo=dt.timezone.utc)
ZULU = "2026-11-25T20:00:00Z"
ZULU_UTC = dt.datetime(2026, 11, 25, 20, 0, tzinfo=dt.timezone.utc)
FRACTIONAL = "2026-11-25T15:00:00.500-04:00"
FRACTIONAL_UTC = dt.datetime(2026, 11, 25, 19, 0, 0, 500000, tzinfo=dt.timezone.utc)


@scenario("timestamps", "iso_inputs_outputs",
          ["create_task", "update_task", "get_task_by_id",
           "create_calendar_event", "get_calendar_event_by_id",
           "create_timeline_activity", "get_timeline_activity_by_id",
           "create_message", "update_message", "get_message_by_id"])
def iso_inputs_outputs(s: Scenario) -> None:
    task_name = s.fixture("date-task")
    task = s.call("create task with offset date", "create_task",
                  {"title": task_name, "status": "todo", "dueAt": OFFSET})
    tid = str(task.data.get("id") or "")
    s.check("dated task has an id", lambda: require(bool(tid), task.data))
    if tid:
        s.own(tid)
        s.cleanup("delete_task_by_id", {"id": tid}, "cleanup dated task")
        got = s.call("get dated task", "get_task_by_id",
                     {"id": tid, "include_all_fields": True}).data
        s.check("offset input preserves the instant",
                lambda: require_instant(got.get("dueAt"), OFFSET_UTC, "dueAt"))
        s.check("date output is ISO with an offset",
                lambda: require_iso(got.get("dueAt"), "dueAt"))
        s.check("date output is UTC",
                lambda: require_utc(got.get("dueAt"), "dueAt"))

        s.call("update task with Z date", "update_task",
               {"id": tid, "dueAt": ZULU})
        updated = s.call("get task after Z update", "get_task_by_id",
                         {"id": tid, "include_all_fields": True}).data
        s.check("Z input preserves the instant",
                lambda: require_instant(updated.get("dueAt"), ZULU_UTC, "dueAt"))

    event_name = s.fixture("date-event")
    event = s.call("create event with fractional offset",
                   "create_calendar_event",
                   {"title": event_name, "startsAt": FRACTIONAL,
                    "endsAt": ZULU})
    eid = str(event.data.get("id") or "")
    s.check("dated event has an id", lambda: require(bool(eid), event.data))
    if eid:
        s.own(eid)
        s.cleanup("delete_calendar_event_by_id", {"id": eid},
                  "cleanup dated event")
        got_event = s.call("get dated event", "get_calendar_event_by_id",
                           {"id": eid, "include_all_fields": True}).data
        s.check("fractional seconds survive the round trip",
                lambda: require_instant(got_event.get("startsAt"),
                                        FRACTIONAL_UTC, "startsAt"))
        s.check("event end instant is preserved",
                lambda: require_instant(got_event.get("endsAt"),
                                        ZULU_UTC, "endsAt"))

    timeline_name = s.fixture("date-timeline")
    timeline = s.call("create timeline with Z date", "create_timeline_activity",
                      {"name": timeline_name, "happensAt": ZULU})
    lid = str(timeline.data.get("id") or "")
    if lid:
        s.own(lid)
        s.cleanup("delete_timeline_activity_by_id", {"id": lid},
                  "cleanup dated timeline")
        got_timeline = s.call("get dated timeline",
                              "get_timeline_activity_by_id",
                              {"id": lid, "include_all_fields": True}).data
        s.check("timeline preserves the Z instant",
                lambda: require_instant(got_timeline.get("happensAt"),
                                        ZULU_UTC, "happensAt"))

    message_name = s.fixture("date-message")
    message = s.call("create dated message", "create_message",
                     {"subject": message_name})
    mid = str(message.data.get("id") or "")
    if mid:
        s.own(mid)
        s.cleanup("delete_message_by_id", {"id": mid}, "cleanup dated message")
        s.call("update message receivedAt", "update_message",
               {"id": mid, "receivedAt": OFFSET})
        got_message = s.call("get dated message", "get_message_by_id",
                             {"id": mid, "include_all_fields": True}).data
        s.check("message receivedAt preserves the instant",
                lambda: require_instant(got_message.get("receivedAt"),
                                        OFFSET_UTC, "receivedAt"))

    for value, label, contains in (
        ("2026-11-25T15:00:00", "naive datetime", ("offset", "ISO 8601", "Invalid datetime")),
        ("2026-11-25", "date-only value", ("offset", "ISO 8601", "Invalid datetime")),
        ("1795638600", "epoch string", ("offset", "ISO 8601", "Invalid datetime")),
        (1795638600, "epoch integer", ("string", "valid", "validation")),
    ):
        s.expect_error(f"rejects {label}", "create_task",
                       {"title": s.fixture("bad-date"), "status": "todo",
                        "dueAt": value},
                       contains=contains)
