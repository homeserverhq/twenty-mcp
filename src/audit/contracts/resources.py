"""CRUD lifecycle contracts for every Twenty resource domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..expect import find_item, require, require_not_contains
from ..harness import Scenario, scenario

NOW = "2026-11-25T15:00:00-04:00"
NOW_END = "2026-11-25T16:00:00-04:00"


@dataclass
class ResourceSpec:
    name: str
    list_tool: str
    get_tool: str
    create_tool: str
    update_tool: str
    delete_tool: str
    create_args: Callable[[Scenario, str, dict[str, Any]], dict[str, Any]]
    update_args: Callable[[Scenario, str, dict[str, Any]], dict[str, Any]]
    changed_field: str
    changed_value: Callable[[str, dict[str, Any]], Any]
    update_many_tool: str | None = None
    delete_many_tool: str | None = None
    setup: Callable[[Scenario], dict[str, Any]] | None = None
    list_visible: bool = True
    list_visibility_note: str = ""

    def tools(self) -> tuple[str, ...]:
        tools = [self.list_tool, self.get_tool, self.create_tool,
                 self.update_tool, self.delete_tool]
        if self.update_many_tool:
            tools.append(self.update_many_tool)
        if self.delete_many_tool:
            tools.append(self.delete_many_tool)
        return tuple(tools)


def _updated(name: str, deps: dict[str, Any]) -> str:
    return f"{name}-updated"


def _note_parent(s: Scenario) -> dict[str, Any]:
    name = s.fixture("note-parent")
    call = s.call("create note parent", "create_note",
                  {"title": name, "markdown": "parent"})
    record_id = str(call.data.get("id") or "")
    s.own(record_id)
    s.cleanup("delete_note_by_id", {"id": record_id}, "cleanup note parent")
    return {"note_id": record_id}


def _task_parent(s: Scenario) -> dict[str, Any]:
    name = s.fixture("task-parent")
    call = s.call("create task parent", "create_task",
                  {"title": name, "status": "todo"})
    record_id = str(call.data.get("id") or "")
    s.own(record_id)
    s.cleanup("delete_task_by_id", {"id": record_id}, "cleanup task parent")
    return {"task_id": record_id}


def _person_parent(s: Scenario) -> dict[str, Any]:
    name = s.fixture("person-parent")
    call = s.call("create person parent", "create_person",
                  {"name": {"firstName": name, "lastName": "Audit"},
                   "emails": {"primaryEmail": f"{name.lower()}@example.com"}})
    record_id = str(call.data.get("id") or "")
    s.own(record_id)
    s.cleanup("delete_person_by_id", {"id": record_id}, "cleanup person parent")
    return {"person_id": record_id}


def _event_parent(s: Scenario) -> dict[str, Any]:
    name = s.fixture("event-parent")
    call = s.call("create calendar event parent", "create_calendar_event",
                  {"title": name, "startsAt": NOW, "endsAt": NOW_END})
    record_id = str(call.data.get("id") or "")
    s.own(record_id)
    s.cleanup("delete_calendar_event_by_id", {"id": record_id},
              "cleanup calendar event parent")
    return {"calendar_event_id": record_id}


def _message_parent(s: Scenario) -> dict[str, Any]:
    name = s.fixture("message-parent")
    call = s.call("create message parent", "create_message", {"subject": name})
    record_id = str(call.data.get("id") or "")
    s.own(record_id)
    s.cleanup("delete_message_by_id", {"id": record_id},
              "cleanup message parent")
    return {"message_id": record_id}


def _note_target_setup(s: Scenario) -> dict[str, Any]:
    deps = _note_parent(s)
    deps.update(_person_parent(s))
    return deps


def _task_target_setup(s: Scenario) -> dict[str, Any]:
    deps = _task_parent(s)
    deps.update(_person_parent(s))
    return deps


SPECS: dict[str, ResourceSpec] = {
    "company": ResourceSpec(
        "company", "list_companies", "get_company_by_id", "create_company",
        "update_company", "delete_company_by_id",
        lambda s, n, d: {"name": n},
        lambda s, n, d: {"name": _updated(n, d)},
        "name", lambda n, d: _updated(n, d),
        "update_companies", "delete_companies",
    ),
    "person": ResourceSpec(
        "person", "list_people", "get_person_by_id", "create_person",
        "update_person", "delete_person_by_id",
        lambda s, n, d: {"name": {"firstName": n, "lastName": "Audit"},
                         "emails": {"primaryEmail": f"{n.lower()}@example.com"}},
        lambda s, n, d: {"jobTitle": "Audit Engineer"},
        "jobTitle", lambda n, d: "Audit Engineer",
        "update_people", "delete_people",
    ),
    "opportunity": ResourceSpec(
        "opportunity", "list_opportunities", "get_opportunity_by_id",
        "create_opportunity", "update_opportunity", "delete_opportunity_by_id",
        lambda s, n, d: {"name": n, "stage": "new"},
        lambda s, n, d: {"stage": "screening"},
        "stage", lambda n, d: "SCREENING",
        "update_opportunities", "delete_opportunities",
    ),
    "note": ResourceSpec(
        "note", "list_notes", "get_note_by_id", "create_note",
        "update_note", "delete_note_by_id",
        lambda s, n, d: {"title": n, "markdown": "audit note body"},
        lambda s, n, d: {"title": _updated(n, d)},
        "title", lambda n, d: _updated(n, d),
        "update_notes", "delete_notes",
    ),
    "task": ResourceSpec(
        "task", "list_tasks", "get_task_by_id", "create_task",
        "update_task", "delete_task_by_id",
        lambda s, n, d: {"title": n, "status": "todo",
                         "markdown": "audit task body"},
        lambda s, n, d: {"status": "in_progress"},
        "status", lambda n, d: "IN_PROGRESS",
        "update_tasks", "delete_tasks",
    ),
    "workflow": ResourceSpec(
        "workflow", "list_workflows", "get_workflow_by_id", "create_workflow",
        "update_workflow", "delete_workflow_by_id",
        lambda s, n, d: {"name": n, "statuses": ["active"]},
        lambda s, n, d: {"name": _updated(n, d)},
        "name", lambda n, d: _updated(n, d),
    ),
    "attachment": ResourceSpec(
        "attachment", "list_attachments", "get_attachment_by_id",
        "create_attachment", "update_attachment", "delete_attachment_by_id",
        lambda s, n, d: {"name": n, "fullPath": f"/tmp/{n}.pdf"},
        lambda s, n, d: {"name": _updated(n, d)},
        "name", lambda n, d: _updated(n, d),
        "update_attachments", "delete_attachments",
    ),
    "noteTarget": ResourceSpec(
        "noteTarget", "list_note_targets", "get_note_target_by_id",
        "create_note_target", "update_note_target", "delete_note_target_by_id",
        lambda s, n, d: {"noteId": d["note_id"]},
        lambda s, n, d: {"targetPersonId": d["person_id"]},
        "targetPersonId", lambda n, d: d["person_id"],
        "update_note_targets", "delete_note_targets",
        _note_target_setup,
    ),
    "taskTarget": ResourceSpec(
        "taskTarget", "list_task_targets", "get_task_target_by_id",
        "create_task_target", "update_task_target", "delete_task_target_by_id",
        lambda s, n, d: {"taskId": d["task_id"]},
        lambda s, n, d: {"targetPersonId": d["person_id"]},
        "targetPersonId", lambda n, d: d["person_id"],
        "update_task_targets", "delete_task_targets",
        _task_target_setup,
    ),
    "timelineActivity": ResourceSpec(
        "timelineActivity", "list_timeline_activities", "get_timeline_activity_by_id",
        "create_timeline_activity", "update_timeline_activity",
        "delete_timeline_activity_by_id",
        lambda s, n, d: {"name": n, "happensAt": NOW},
        lambda s, n, d: {"name": _updated(n, d)},
        "name", lambda n, d: _updated(n, d),
        "update_timeline_activities", "delete_timeline_activities",
    ),
    "calendarEvent": ResourceSpec(
        "calendarEvent", "list_calendar_events", "get_calendar_event_by_id",
        "create_calendar_event", "update_calendar_event",
        "delete_calendar_event_by_id",
        lambda s, n, d: {"title": n, "startsAt": NOW, "endsAt": NOW_END},
        lambda s, n, d: {"title": _updated(n, d)},
        "title", lambda n, d: _updated(n, d),
        "update_calendar_events", "delete_calendar_events",
    ),
    "calendarEventParticipant": ResourceSpec(
        "calendarEventParticipant", "list_calendar_event_participants",
        "get_calendar_event_participant_by_id",
        "create_calendar_event_participant",
        "update_calendar_event_participant",
        "delete_calendar_event_participant_by_id",
        lambda s, n, d: {"calendarEventId": d["calendar_event_id"],
                         "handle": f"{n.lower()}@example.com",
                         "displayName": n},
        lambda s, n, d: {"displayName": _updated(n, d)},
        "displayName", lambda n, d: _updated(n, d),
        "update_calendar_event_participants",
        "delete_calendar_event_participants",
        _event_parent,
    ),
    "message": ResourceSpec(
        "message", "list_messages", "get_message_by_id", "create_message",
        "update_message", "delete_message_by_id",
        lambda s, n, d: {"subject": n},
        lambda s, n, d: {"subject": _updated(n, d)},
        "subject", lambda n, d: _updated(n, d),
        "update_messages", "delete_messages",
    ),
    "messageThread": ResourceSpec(
        "messageThread", "list_message_threads", "get_message_thread_by_id",
        "create_message_thread", "update_message_thread",
        "delete_message_thread_by_id",
        lambda s, n, d: {"subject": n},
        lambda s, n, d: {"subject": _updated(n, d)},
        "subject", lambda n, d: _updated(n, d),
        "update_message_threads", "delete_message_threads",
    ),
    "messageParticipant": ResourceSpec(
        "messageParticipant", "list_message_participants",
        "get_message_participant_by_id", "create_message_participant",
        "update_message_participant", "delete_message_participant_by_id",
        lambda s, n, d: {"messageId": d["message_id"], "role": "from",
                         "handle": f"{n.lower()}@example.com",
                         "displayName": n},
        lambda s, n, d: {"displayName": _updated(n, d)},
        "displayName", lambda n, d: _updated(n, d),
        "update_message_participants", "delete_message_participants",
        _message_parent,
    ),
    "callRecording": ResourceSpec(
        "callRecording", "list_call_recordings", "get_call_recording_by_id",
        "create_call_recording", "update_call_recording",
        "delete_call_recording_by_id",
        lambda s, n, d: {"title": n, "status": "recording"},
        lambda s, n, d: {"status": "completed"},
        "status", lambda n, d: "COMPLETED",
        "update_call_recordings", "delete_call_recordings",
    ),
}


def _find_in_pages(s: Scenario, tool: str, target: str,
                   extra: dict[str, Any] | None = None,
                   field: str = "id", max_pages: int = 10) -> list[dict[str, Any]]:
    cursor: str | None = None
    collected: list[dict[str, Any]] = []
    for _ in range(max_pages):
        args = {"limit": 200, **(extra or {})}
        if cursor:
            args["starting_after"] = cursor
        _, items, _, page_info = s.page(f"{tool} page", tool, args)
        collected.extend(item for item in items if isinstance(item, dict))
        if any(str(item.get(field)) == str(target) for item in collected):
            return collected
        cursor = page_info.get("endCursor")
        if not page_info.get("hasNextPage") or not cursor:
            break
    return collected


def _lifecycle(s: Scenario, spec: ResourceSpec) -> None:
    deps = spec.setup(s) if spec.setup else {}
    name = s.fixture(spec.name)

    created = s.call(f"create {spec.name}", spec.create_tool,
                     spec.create_args(s, name, deps))
    rid = str(created.data.get("id") or "")
    s.check(f"{spec.name} create returns an id",
            lambda: require(bool(rid), created.data))
    if not rid:
        return
    s.own(rid)
    s.cleanup(spec.delete_tool, {"id": rid}, f"cleanup {spec.name} 1")

    second = s.call(f"create second {spec.name}", spec.create_tool,
                    spec.create_args(s, name + "-2", deps))
    rid2 = str(second.data.get("id") or "")
    s.check(f"{spec.name} second create returns an id",
            lambda: require(bool(rid2), second.data))
    if rid2:
        s.own(rid2)
        s.cleanup(spec.delete_tool, {"id": rid2}, f"cleanup {spec.name} 2")

    got = s.call(f"get {spec.name}", spec.get_tool,
                 {"id": rid, "include_all_fields": True})
    s.check(f"get {spec.name} returns the created record",
            lambda: require(str(got.data.get("id")) == rid, got.data))

    if spec.list_visible:
        listed = _find_in_pages(s, spec.list_tool, rid)
        s.check(f"{spec.name} appears in its list",
                lambda: require(any(str(item.get("id")) == rid for item in listed),
                                f"first ids: {[i.get('id') for i in listed[:5]]}"))
    else:
        list_call = s.call(f"{spec.name} list envelope", spec.list_tool,
                           {"limit": 200})
        s.items(f"{spec.name} list decodes", list_call)
        s.check(f"{spec.name} list warns about hidden rows",
                lambda: require(bool(list_call.data.get("warning")),
                                list_call.data))
        s.skip(f"{spec.name} appears in its list",
               spec.list_visibility_note or "backend list omits this record")

    update_args = spec.update_args(s, name, deps)
    s.call(f"update {spec.name}", spec.update_tool, {"id": rid, **update_args})
    after = s.call(f"get updated {spec.name}", spec.get_tool,
                   {"id": rid, "include_all_fields": True})
    expected = spec.changed_value(name, deps)
    s.check(f"update {spec.name} is persisted",
            lambda: require(after.data.get(spec.changed_field) == expected,
                            f"{spec.changed_field}={after.data.get(spec.changed_field)!r}, "
                            f"expected {expected!r}"))

    if spec.update_many_tool and rid2:
        s.call(f"bulk update {spec.name}", spec.update_many_tool,
               {"ids": [rid, rid2], **update_args})
        for label, record_id in (("first", rid), ("second", rid2)):
            after_bulk = s.call(f"get bulk-updated {spec.name} {label}",
                                spec.get_tool,
                                {"id": record_id, "include_all_fields": True})
            s.check(f"bulk update persisted on {label} {spec.name}",
                    lambda data=after_bulk.data: require(
                        data.get(spec.changed_field) == expected,
                        f"{spec.changed_field}={data.get(spec.changed_field)!r}, "
                        f"expected {expected!r}",
                    ))

    s.call(f"delete {spec.name}", spec.delete_tool, {"id": rid})
    s.expect_error(f"deleted {spec.name} is not gettable", spec.get_tool,
                   {"id": rid, "include_all_fields": True})
    if spec.list_visible:
        remaining = _find_in_pages(s, spec.list_tool, rid)
        s.check(f"deleted {spec.name} is absent from its list",
                lambda: require(
                    not any(str(item.get("id")) == rid for item in remaining),
                    "still listed",
                ))
    else:
        s.skip(f"deleted {spec.name} is absent from its list",
               spec.list_visibility_note or "list visibility gap")

    if spec.delete_many_tool and rid2:
        deleted = s.call(f"bulk delete {spec.name}", spec.delete_many_tool,
                         {"ids": [rid2]})
        s.check(f"bulk delete {spec.name} reports one deletion",
                lambda: require(deleted.data.get("count") == 1, deleted.data))
        s.expect_error(f"bulk-deleted {spec.name} is not gettable",
                       spec.get_tool, {"id": rid2, "include_all_fields": True})
    elif rid2:
        s.call(f"delete second {spec.name}", spec.delete_tool, {"id": rid2})
        s.expect_error(f"second {spec.name} is not gettable", spec.get_tool,
                       {"id": rid2, "include_all_fields": True})


def _register(spec: ResourceSpec) -> None:
    @scenario("resources", f"crud_{spec.name}", spec.tools())
    def _run(s: Scenario, spec: ResourceSpec = spec) -> None:
        _lifecycle(s, spec)


SPECS["message"].list_visible = False
SPECS["message"].list_visibility_note = (
    "Twenty's message list joins messageChannelMessageAssociation; this "
    "workspace has no message channels, so list returns totalCount>0 with "
    "zero rows while get-by-id works. Backend association gap, not a TOON bug."
)
SPECS["calendarEvent"].list_visible = False
SPECS["calendarEvent"].list_visibility_note = (
    "Twenty's calendar-event list joins calendarChannelEventAssociation; an "
    "event created through this MCP has no association, so list omits it "
    "while get-by-id returns it. Backend association gap."
)

for _spec in SPECS.values():
    _register(_spec)
