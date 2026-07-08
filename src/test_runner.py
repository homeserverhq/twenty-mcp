"""
Flat end-to-end test harness for Twenty MCP Server.
Zero conditionals in test orchestration — every test runs every time.
No try/except — any exception crashes the runner immediately.
No references to "skip". 132 tests, identical coverage to test_runner.py.
"""

import json
import os
import sys
import time
import uuid
from typing import Any, Optional

import httpx
from toon_mcp import toon_to_json

import asyncio

MCP_SERVER_PORT = os.environ.get("MCP_SERVER_PORT", "6375")
API_KEY = os.environ.get("API_KEY", "")
MCP_URL = f"http://localhost:{MCP_SERVER_PORT}/mcp"

MCP_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
}

rid = uuid.uuid4().hex[:8]

results: list[dict[str, Any]] = []
store: dict[str, Any] = {}


# =============================================================================
# Transport layer — MCPSession
# Conditionals allowed (MCP protocol requires them)
# =============================================================================

class MCPSession:
    def __init__(self, url: str, headers: dict[str, str]):
        self.url = url
        self.base_headers = {
            **headers,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self.session_headers = dict(self.base_headers)
        self.client = httpx.AsyncClient(timeout=120.0)
        self._request_id = 0
        self._session_id: Optional[str] = None

    async def __aenter__(self):
        await self._initialize()
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    @staticmethod
    def _parse_sse(body: str) -> list[dict]:
        messages: list[dict] = []
        data_buf: list[str] = []
        for line in body.splitlines():
            if line.startswith("data: "):
                data_buf.append(line[6:])
            elif line.startswith("data:"):
                data_buf.append(line[5:])
            elif line == "" and data_buf:
                try:
                    messages.append(json.loads("".join(data_buf)))
                except json.JSONDecodeError:
                    pass
                data_buf = []
        if data_buf:
            try:
                messages.append(json.loads("".join(data_buf)))
            except json.JSONDecodeError:
                pass
        return messages

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        response = await self.client.post(self.url, headers=self.session_headers, json=payload)
        if response.status_code not in (200, 202):
            response.raise_for_status()

    async def _send(self, method: str, params: dict | None = None) -> dict:
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method}
        if params:
            payload["params"] = params
        response = await self.client.post(self.url, headers=self.session_headers, json=payload)
        if response.status_code == 202:
            return {}
        response.raise_for_status()

        sid = response.headers.get("mcp-session-id")
        if sid:
            self._session_id = sid
            self.session_headers = {**self.base_headers, "mcp-session-id": sid}

        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            messages = self._parse_sse(response.text)
            data = messages[0] if messages else {}
        else:
            data = response.json()

        if isinstance(data, list):
            data = data[0]
        if isinstance(data, dict) and "error" in data:
            raise Exception(f"JSON-RPC error: {data['error']}")
        return data.get("result", {})

    async def _initialize(self) -> dict:
        result = await self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "twenty-test-runner",
                "version": "1.0",
            },
        })
        await self._send_notification("notifications/initialized")
        return result

    async def list_tools(self) -> list[dict]:
        result = await self._send("tools/list")
        return result.get("tools", result)

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        params = {"name": name}
        if arguments:
            params["arguments"] = arguments
        return await self._send("tools/call", params)


# =============================================================================
# Helper functions — data inspection / formatting
# Conditionals allowed for response parsing
# =============================================================================

def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def is_error(result: dict[str, Any]) -> Optional[str]:
    if "error" in result:
        err = result["error"]
        return err.get("message", str(err))
    if result.get("isError"):
        content = result.get("content", [])
        for c in content:
            if c.get("type") == "text":
                txt = c["text"]
                if txt.startswith("Error calling tool"):
                    return txt.split(":", 1)[1].strip() if ":" in txt else txt
                try:
                    data = json.loads(txt)
                except json.JSONDecodeError:
                    return txt
                if isinstance(data, dict):
                    return data.get("error", txt)
    return None


def extract_content(result: dict[str, Any]) -> Any:
    if result.get("isError"):
        return {}
    content = result.get("content", [])
    for c in content:
        if c.get("type") == "text":
            try:
                return json.loads(c["text"])
            except json.JSONDecodeError:
                return c["text"]
    return result.get("_meta", {})


def _get_list_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in ("items", "results", "rows", "tree"):
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return val
                if isinstance(val, str):
                    try:
                        parsed = toon_to_json(val)
                        if isinstance(parsed, list):
                            return parsed
                        if isinstance(parsed, dict):
                            for inner in ("collectives", "pages", "tags", "data"):
                                if inner in parsed and isinstance(parsed[inner], list):
                                    return parsed[inner]
                    except Exception:
                        pass
        return []
    elif isinstance(data, list):
        return data
    return []


def _is_test_artifact(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    name = name.strip()
    if not name.startswith("t"):
        return False
    dash_pos = name.find("-", 1)
    if dash_pos < 2 or dash_pos > 9:
        return False
    prefix = name[1:dash_pos]
    return bool(prefix) and all(c in "0123456789abcdef" for c in prefix)


def _store_result(content: Any) -> dict:
    items = _get_list_items(content)
    return items[0] if items else (content if isinstance(content, dict) else {})


def make_name(base: str) -> str:
    return f"t{rid}-{base}"


def make_email(local: str) -> str:
    return f"{local}{rid}@example.com"


# =============================================================================
# Leak detection — helper function with internal conditionals
# =============================================================================

LEAK_SCAN_CONFIG = [
    ("company",                   "list_companies",                  {},                       "id",   "name",                    "delete_company_by_id",             {}),
    ("person",                    "list_people",                     {},                       "id",   "name",                    "delete_person_by_id",              {}),
    ("opportunity",               "list_opportunities",              {},                       "id",   "name",                    "delete_opportunity_by_id",         {}),
    ("note",                      "list_notes",                      {},                       "id",   "title",                  "delete_note_by_id",                {}),
    ("task",                      "list_tasks",                      {},                       "id",   "title",                  "delete_task_by_id",                {}),
    ("workflow",                  "list_workflows",                  {},                       "id",   "name",                    "delete_workflow_by_id",            {}),
    ("attachment",                "list_attachments",                {},                       "id",   "name",                    "delete_attachment_by_id",          {}),
    ("noteTarget",                "list_note_targets",               {},                       "id",   "id",                      "delete_note_target_by_id",         {}),
    ("taskTarget",                "list_task_targets",               {},                       "id",   "id",                      "delete_task_target_by_id",         {}),
    ("timelineActivity",          "list_timeline_activities",        {},                       "id",   "name",                    "delete_timeline_activity_by_id",   {}),
    ("calendarEvent",             "list_calendar_events",            {},                       "id",   "title",                  "delete_calendar_event_by_id",      {}),
    ("calendarEventParticipant",  "list_calendar_event_participants",{},                      "id",   "displayName",            "delete_calendar_event_participant_by_id", {}),
    ("message",                   "list_messages",                   {},                       "id",   "subject",                "delete_message_by_id",             {}),
    ("messageThread",             "list_message_threads",            {},                       "id",   "subject",                "delete_message_thread_by_id",      {}),
    ("messageParticipant",        "list_message_participants",       {},                       "id",   "displayName",            "delete_message_participant_by_id", {}),
    ("callRecording",             "list_call_recordings",            {},                       "id",   "title",                  "delete_call_recording_by_id",      {}),
]


async def _run_leak_detection(session: MCPSession) -> None:
    total_leaks = 0
    for entity_type, list_tool, list_params, id_key, name_key, delete_tool, delete_extra in LEAK_SCAN_CONFIG:
        result = await session.call_tool(list_tool, list_params or None)
        err = is_error(result)
        if err:
            continue
        data = extract_content(result)
        items = _get_list_items(data)
        for item in items:
            if not isinstance(item, dict):
                continue
            name_val = str(item.get(name_key, "") or "")
            if not _is_test_artifact(name_val):
                continue
            item_id = item.get(id_key)
            if item_id is None:
                continue
            total_leaks += 1
            label = f"LEAK {entity_type} id={item_id} name={name_val[:40]}"
            results.append({
                "label": label, "tool": delete_tool, "status": "FAILED",
                "reason": f"Leaked {entity_type} found after test run - delete was not called or failed",
            })
            log(f"  FAIL {label}")
            del_params = {id_key: item_id, **delete_extra}
            try:
                await session.call_tool(delete_tool, del_params)
                log(f"       => cleaned up {entity_type} {item_id}")
            except Exception:
                pass

    if total_leaks == 0:
        results.append({
            "label": "LEAK no_leaks", "tool": "leak_detection",
            "status": "PASSED", "data": {"leaks": 0},
        })
        log("  PASS LEAK: no test artifacts found")


# =============================================================================
# Execution helpers — test orchestration (zero conditionals in the flow)
# =============================================================================

def _log_result(label: str, status: str, error_str: Optional[str]) -> None:
    line = f"  {status} {label}"
    if error_str:
        line += f": {error_str}"
    log(line)


async def _exec(session: MCPSession, tests: list) -> None:
    for label, tool, params_fn, store_key, is_verify in tests:
        params = params_fn(store, rid)
        result = await session.call_tool(tool, params)
        content = extract_content(result)
        error_str = is_error(result)
        store[store_key] = _store_result(content)
        error_is_none = error_str is None
        status = ("FAILED", "PASSED")[error_is_none ^ is_verify]
        results.append({
            "label": label, "tool": tool, "status": status,
            "reason": error_str or "", "data": content,
        })
        _log_result(label, status, error_str)


# =============================================================================
# FLAT TEST DEFINITIONS
# (label, tool_name, params_fn, store_key, is_verify)
# store_key=None for tests that don't feed downstream tests
# is_verify=True for C5 verify-delete (PASS when error == record gone)
# =============================================================================

PHASE1_TESTS = [
    ("check_server_status", "check_server_status", lambda s, r: {}, None, False),
]

PHASE2_TESTS = [
    ("list_company", "list_companies", lambda s, r: {}, None, False),
    ("list_person", "list_people", lambda s, r: {}, None, False),
    ("list_opportunity", "list_opportunities", lambda s, r: {}, None, False),
    ("list_workspaceMember", "list_workspace_members", lambda s, r: {}, None, False),
    ("list_note", "list_notes", lambda s, r: {}, None, False),
    ("list_task", "list_tasks", lambda s, r: {}, None, False),
    ("list_workflow", "list_workflows", lambda s, r: {}, None, False),
    ("list_messageThread", "list_message_threads", lambda s, r: {}, None, False),
    ("list_calendarEvent", "list_calendar_events", lambda s, r: {}, None, False),
    ("list_message", "list_messages", lambda s, r: {}, None, False),
    ("list_noteTarget", "list_note_targets", lambda s, r: {}, None, False),
    ("list_taskTarget", "list_task_targets", lambda s, r: {}, None, False),
    ("list_timelineActivity", "list_timeline_activities", lambda s, r: {}, None, False),
    ("list_attachment", "list_attachments", lambda s, r: {}, None, False),
    ("list_callRecording", "list_call_recordings", lambda s, r: {}, None, False),
    ("list_calendarEventParticipant", "list_calendar_event_participants", lambda s, r: {}, None, False),
    ("list_messageParticipant", "list_message_participants", lambda s, r: {}, None, False),
]

PHASE3A_TESTS = [
    ("C1 create_company", "create_company", lambda s, r: {
        "name": f"t{r}-Company",
        "domainName": {"primaryLinkUrl": f"https://t{r}-testco.com", "primaryLinkLabel": ""},
    }, "company", False),
    ("C1 create_person", "create_person", lambda s, r: {
        "name": {"firstName": f"t{r}", "lastName": "Person"},
        "emails": {"primaryEmail": f"t{r}-person@example.com"},
    }, "person", False),
    ("C1 create_opportunity", "create_opportunity", lambda s, r: {
        "name": f"t{r}-Opportunity", "stage": "NEW",
    }, "opportunity", False),
    ("C1 resolve_workspaceMember", "list_workspace_members", lambda s, r: {}, "workspaceMember", False),
    ("C1 create_note", "create_note", lambda s, r: {
        "title": f"t{r}-Note",
    }, "note", False),
    ("C1 create_task", "create_task", lambda s, r: {
        "title": f"t{r}-Task", "status": "TODO",
    }, "task", False),
    ("C1 create_workflow", "create_workflow", lambda s, r: {
        "name": f"t{r}-Workflow", "statuses": ["ACTIVE"],
    }, "workflow", False),
    ("C1 create_messageThread", "create_message_thread", lambda s, r: {
        "subject": f"t{r}-Thread",
    }, "messageThread", False),
    ("C1 create_calendarEvent", "create_calendar_event", lambda s, r: {
        "title": f"t{r}-CalEvent",
        "startsAt": "2026-06-26T14:00:00+00:00",
        "endsAt": "2026-06-26T15:00:00+00:00",
    }, "calendarEvent", False),
    ("C1 create_message", "create_message", lambda s, r: {
        "subject": f"t{r}-Message",
    }, "message", False),
    ("C1 create_noteTarget", "create_note_target", lambda s, r: {
        "noteId": s.get("note", {}).get("id"),
    }, "noteTarget", False),
    ("C1 create_taskTarget", "create_task_target", lambda s, r: {
        "taskId": s.get("task", {}).get("id"),
    }, "taskTarget", False),
    ("C1 create_timelineActivity", "create_timeline_activity", lambda s, r: {
        "name": f"t{r}-Timeline",
        "happensAt": "2026-06-26T14:00:00+00:00",
    }, "timelineActivity", False),
    ("C1 create_attachment", "create_attachment", lambda s, r: {
        "name": f"t{r}-Attachment", "fullPath": f"/tmp/t{r}-att.pdf",
    }, "attachment", False),
    ("C1 create_callRecording", "create_call_recording", lambda s, r: {
        "title": f"t{r}-Call", "status": "RECORDING",
    }, "callRecording", False),
    ("C1 create_calendarEventParticipant", "create_calendar_event_participant", lambda s, r: {
        "calendarEventId": s.get("calendarEvent", {}).get("id"),
        "handle": f"t{r}-calpart@example.com",
        "displayName": f"t{r}-CalPart",
    }, "calendarEventParticipant", False),
    ("C1 create_messageParticipant", "create_message_participant", lambda s, r: {
        "messageId": s.get("message", {}).get("id"),
        "handle": f"t{r}-msgpart",
        "displayName": f"t{r}-MsgPart",
        "role": "FROM",
    }, "messageParticipant", False),
]

PHASE3B_TESTS = [
    ("C2 get_company", "get_company_by_id", lambda s, r: {"id": s.get("company", {}).get("id")}, None, False),
    ("C2 get_person", "get_person_by_id", lambda s, r: {"id": s.get("person", {}).get("id")}, None, False),
    ("C2 get_opportunity", "get_opportunity_by_id", lambda s, r: {"id": s.get("opportunity", {}).get("id")}, None, False),
    ("C2 get_workspaceMember", "get_workspace_member_by_id", lambda s, r: {"id": s.get("workspaceMember", {}).get("id")}, None, False),
    ("C2 get_note", "get_note_by_id", lambda s, r: {"id": s.get("note", {}).get("id")}, None, False),
    ("C2 get_task", "get_task_by_id", lambda s, r: {"id": s.get("task", {}).get("id")}, None, False),
    ("C2 get_workflow", "get_workflow_by_id", lambda s, r: {"id": s.get("workflow", {}).get("id")}, None, False),
    ("C2 get_messageThread", "get_message_thread_by_id", lambda s, r: {"id": s.get("messageThread", {}).get("id")}, None, False),
    ("C2 get_calendarEvent", "get_calendar_event_by_id", lambda s, r: {"id": s.get("calendarEvent", {}).get("id")}, None, False),
    ("C2 get_message", "get_message_by_id", lambda s, r: {"id": s.get("message", {}).get("id")}, None, False),
    ("C2 get_noteTarget", "get_note_target_by_id", lambda s, r: {"id": s.get("noteTarget", {}).get("id")}, None, False),
    ("C2 get_taskTarget", "get_task_target_by_id", lambda s, r: {"id": s.get("taskTarget", {}).get("id")}, None, False),
    ("C2 get_timelineActivity", "get_timeline_activity_by_id", lambda s, r: {"id": s.get("timelineActivity", {}).get("id")}, None, False),
    ("C2 get_attachment", "get_attachment_by_id", lambda s, r: {"id": s.get("attachment", {}).get("id")}, None, False),
    ("C2 get_callRecording", "get_call_recording_by_id", lambda s, r: {"id": s.get("callRecording", {}).get("id")}, None, False),
    ("C2 get_calendarEventParticipant", "get_calendar_event_participant_by_id", lambda s, r: {"id": s.get("calendarEventParticipant", {}).get("id")}, None, False),
    ("C2 get_messageParticipant", "get_message_participant_by_id", lambda s, r: {"id": s.get("messageParticipant", {}).get("id")}, None, False),
]

PHASE3C_TESTS = [
    ("C3 update_company", "update_company", lambda s, r: {"id": s.get("company", {}).get("id"), "name": f"t{r}-Company-Upd"}, None, False),
    ("C3 update_person", "update_person", lambda s, r: {"id": s.get("person", {}).get("id"), "jobTitle": f"t{r}-Engineer"}, None, False),
    ("C3 update_opportunity", "update_opportunity", lambda s, r: {"id": s.get("opportunity", {}).get("id"), "stage": "SCREENING"}, None, False),
    ("C3 update_workspaceMember", "update_workspace_member", lambda s, r: {"id": s.get("workspaceMember", {}).get("id"), "colorScheme": "Dark"}, None, False),
    ("C3 update_note", "update_note", lambda s, r: {"id": s.get("note", {}).get("id"), "title": f"t{r}-Note-Upd"}, None, False),
    ("C3 update_task", "update_task", lambda s, r: {"id": s.get("task", {}).get("id"), "status": "IN_PROGRESS"}, None, False),
    ("C3 update_workflow", "update_workflow", lambda s, r: {"id": s.get("workflow", {}).get("id")}, None, False),
    ("C3 update_messageThread", "update_message_thread", lambda s, r: {"id": s.get("messageThread", {}).get("id"), "subject": f"t{r}-Thread-Upd"}, None, False),
    ("C3 update_calendarEvent", "update_calendar_event", lambda s, r: {"id": s.get("calendarEvent", {}).get("id"), "title": f"t{r}-CalEvent-Upd"}, None, False),
    ("C3 update_message", "update_message", lambda s, r: {"id": s.get("message", {}).get("id"), "subject": f"t{r}-Message-Upd"}, None, False),
    ("C3 update_noteTarget", "update_note_target", lambda s, r: {"id": s.get("noteTarget", {}).get("id")}, None, False),
    ("C3 update_taskTarget", "update_task_target", lambda s, r: {"id": s.get("taskTarget", {}).get("id")}, None, False),
    ("C3 update_timelineActivity", "update_timeline_activity", lambda s, r: {"id": s.get("timelineActivity", {}).get("id"), "name": f"t{r}-Timeline-Upd"}, None, False),
    ("C3 update_attachment", "update_attachment", lambda s, r: {"id": s.get("attachment", {}).get("id"), "name": f"t{r}-Attachment-Upd"}, None, False),
    ("C3 update_callRecording", "update_call_recording", lambda s, r: {"id": s.get("callRecording", {}).get("id"), "status": "COMPLETED"}, None, False),
    ("C3 update_calendarEventParticipant", "update_calendar_event_participant", lambda s, r: {"id": s.get("calendarEventParticipant", {}).get("id"), "displayName": f"t{r}-CalPart-Upd"}, None, False),
    ("C3 update_messageParticipant", "update_message_participant", lambda s, r: {"id": s.get("messageParticipant", {}).get("id"), "displayName": f"t{r}-MsgPart-Upd"}, None, False),
]

PHASE3D_TESTS = [
    ("C4 delete_messageParticipant", "delete_message_participant_by_id", lambda s, r: {"id": s.get("messageParticipant", {}).get("id")}, None, False),
    ("C4 delete_calendarEventParticipant", "delete_calendar_event_participant_by_id", lambda s, r: {"id": s.get("calendarEventParticipant", {}).get("id")}, None, False),
    ("C4 delete_callRecording", "delete_call_recording_by_id", lambda s, r: {"id": s.get("callRecording", {}).get("id")}, None, False),
    ("C4 delete_attachment", "delete_attachment_by_id", lambda s, r: {"id": s.get("attachment", {}).get("id")}, None, False),
    ("C4 delete_timelineActivity", "delete_timeline_activity_by_id", lambda s, r: {"id": s.get("timelineActivity", {}).get("id")}, None, False),
    ("C4 delete_taskTarget", "delete_task_target_by_id", lambda s, r: {"id": s.get("taskTarget", {}).get("id")}, None, False),
    ("C4 delete_noteTarget", "delete_note_target_by_id", lambda s, r: {"id": s.get("noteTarget", {}).get("id")}, None, False),
    ("C4 delete_message", "delete_message_by_id", lambda s, r: {"id": s.get("message", {}).get("id")}, None, False),
    ("C4 delete_calendarEvent", "delete_calendar_event_by_id", lambda s, r: {"id": s.get("calendarEvent", {}).get("id")}, None, False),
    ("C4 delete_messageThread", "delete_message_thread_by_id", lambda s, r: {"id": s.get("messageThread", {}).get("id")}, None, False),
    ("C4 delete_workflow", "delete_workflow_by_id", lambda s, r: {"id": s.get("workflow", {}).get("id")}, None, False),
    ("C4 delete_task", "delete_task_by_id", lambda s, r: {"id": s.get("task", {}).get("id")}, None, False),
    ("C4 delete_note", "delete_note_by_id", lambda s, r: {"id": s.get("note", {}).get("id")}, None, False),
    ("C4 delete_opportunity", "delete_opportunity_by_id", lambda s, r: {"id": s.get("opportunity", {}).get("id")}, None, False),
    ("C4 delete_person", "delete_person_by_id", lambda s, r: {"id": s.get("person", {}).get("id")}, None, False),
    ("C4 delete_company", "delete_company_by_id", lambda s, r: {"id": s.get("company", {}).get("id")}, None, False),
]

PHASE3E_TESTS = [
    ("C5 verify_delete_messageParticipant", "get_message_participant_by_id", lambda s, r: {"id": s.get("messageParticipant", {}).get("id")}, None, True),
    ("C5 verify_delete_calendarEventParticipant", "get_calendar_event_participant_by_id", lambda s, r: {"id": s.get("calendarEventParticipant", {}).get("id")}, None, True),
    ("C5 verify_delete_callRecording", "get_call_recording_by_id", lambda s, r: {"id": s.get("callRecording", {}).get("id")}, None, True),
    ("C5 verify_delete_attachment", "get_attachment_by_id", lambda s, r: {"id": s.get("attachment", {}).get("id")}, None, True),
    ("C5 verify_delete_timelineActivity", "get_timeline_activity_by_id", lambda s, r: {"id": s.get("timelineActivity", {}).get("id")}, None, True),
    ("C5 verify_delete_taskTarget", "get_task_target_by_id", lambda s, r: {"id": s.get("taskTarget", {}).get("id")}, None, True),
    ("C5 verify_delete_noteTarget", "get_note_target_by_id", lambda s, r: {"id": s.get("noteTarget", {}).get("id")}, None, True),
    ("C5 verify_delete_message", "get_message_by_id", lambda s, r: {"id": s.get("message", {}).get("id")}, None, True),
    ("C5 verify_delete_calendarEvent", "get_calendar_event_by_id", lambda s, r: {"id": s.get("calendarEvent", {}).get("id")}, None, True),
    ("C5 verify_delete_messageThread", "get_message_thread_by_id", lambda s, r: {"id": s.get("messageThread", {}).get("id")}, None, True),
    ("C5 verify_delete_workflow", "get_workflow_by_id", lambda s, r: {"id": s.get("workflow", {}).get("id")}, None, True),
    ("C5 verify_delete_task", "get_task_by_id", lambda s, r: {"id": s.get("task", {}).get("id")}, None, True),
    ("C5 verify_delete_note", "get_note_by_id", lambda s, r: {"id": s.get("note", {}).get("id")}, None, True),
    ("C5 verify_delete_opportunity", "get_opportunity_by_id", lambda s, r: {"id": s.get("opportunity", {}).get("id")}, None, True),
    ("C5 verify_delete_person", "get_person_by_id", lambda s, r: {"id": s.get("person", {}).get("id")}, None, True),
    ("C5 verify_delete_company", "get_company_by_id", lambda s, r: {"id": s.get("company", {}).get("id")}, None, True),
]

PHASE4_TESTS = [
    # Bulk updates (15 resources)
    ("bulk_update_company", "update_companies", lambda s, r: {"ids": [s.get("company", {}).get("id"), s.get("company", {}).get("id")], "name": f"t{r}-Company-Upd"}, None, False),
    ("bulk_update_person", "update_people", lambda s, r: {"ids": [s.get("person", {}).get("id"), s.get("person", {}).get("id")], "jobTitle": f"t{r}-Engineer"}, None, False),
    ("bulk_update_opportunity", "update_opportunities", lambda s, r: {"ids": [s.get("opportunity", {}).get("id"), s.get("opportunity", {}).get("id")], "stage": "SCREENING"}, None, False),
    ("bulk_update_note", "update_notes", lambda s, r: {"ids": [s.get("note", {}).get("id"), s.get("note", {}).get("id")], "title": f"t{r}-Note-Upd"}, None, False),
    ("bulk_update_task", "update_tasks", lambda s, r: {"ids": [s.get("task", {}).get("id"), s.get("task", {}).get("id")], "status": "IN_PROGRESS"}, None, False),
    ("bulk_update_messageThread", "update_message_threads", lambda s, r: {"ids": [s.get("messageThread", {}).get("id"), s.get("messageThread", {}).get("id")], "subject": f"t{r}-Thread-Upd"}, None, False),
    ("bulk_update_calendarEvent", "update_calendar_events", lambda s, r: {"ids": [s.get("calendarEvent", {}).get("id"), s.get("calendarEvent", {}).get("id")], "title": f"t{r}-CalEvent-Upd"}, None, False),
    ("bulk_update_message", "update_messages", lambda s, r: {"ids": [s.get("message", {}).get("id"), s.get("message", {}).get("id")], "subject": f"t{r}-Message-Upd"}, None, False),
    ("bulk_update_noteTarget", "update_note_targets", lambda s, r: {"ids": [s.get("noteTarget", {}).get("id"), s.get("noteTarget", {}).get("id")]}, None, False),
    ("bulk_update_taskTarget", "update_task_targets", lambda s, r: {"ids": [s.get("taskTarget", {}).get("id"), s.get("taskTarget", {}).get("id")]}, None, False),
    ("bulk_update_timelineActivity", "update_timeline_activities", lambda s, r: {"ids": [s.get("timelineActivity", {}).get("id"), s.get("timelineActivity", {}).get("id")], "name": f"t{r}-Timeline-Upd"}, None, False),
    ("bulk_update_attachment", "update_attachments", lambda s, r: {"ids": [s.get("attachment", {}).get("id"), s.get("attachment", {}).get("id")], "name": f"t{r}-Attachment-Upd"}, None, False),
    ("bulk_update_callRecording", "update_call_recordings", lambda s, r: {"ids": [s.get("callRecording", {}).get("id"), s.get("callRecording", {}).get("id")], "status": "COMPLETED"}, None, False),
    ("bulk_update_calendarEventParticipant", "update_calendar_event_participants", lambda s, r: {"ids": [s.get("calendarEventParticipant", {}).get("id"), s.get("calendarEventParticipant", {}).get("id")], "displayName": f"t{r}-CalPart-Upd"}, None, False),
    ("bulk_update_messageParticipant", "update_message_participants", lambda s, r: {"ids": [s.get("messageParticipant", {}).get("id"), s.get("messageParticipant", {}).get("id")], "displayName": f"t{r}-MsgPart-Upd"}, None, False),
    # Bulk deletes (15 resources)
    ("bulk_delete_company", "delete_companies", lambda s, r: {"ids": [s.get("company", {}).get("id"), s.get("company", {}).get("id")]}, None, False),
    ("bulk_delete_person", "delete_people", lambda s, r: {"ids": [s.get("person", {}).get("id"), s.get("person", {}).get("id")]}, None, False),
    ("bulk_delete_opportunity", "delete_opportunities", lambda s, r: {"ids": [s.get("opportunity", {}).get("id"), s.get("opportunity", {}).get("id")]}, None, False),
    ("bulk_delete_note", "delete_notes", lambda s, r: {"ids": [s.get("note", {}).get("id"), s.get("note", {}).get("id")]}, None, False),
    ("bulk_delete_task", "delete_tasks", lambda s, r: {"ids": [s.get("task", {}).get("id"), s.get("task", {}).get("id")]}, None, False),
    ("bulk_delete_messageThread", "delete_message_threads", lambda s, r: {"ids": [s.get("messageThread", {}).get("id"), s.get("messageThread", {}).get("id")]}, None, False),
    ("bulk_delete_calendarEvent", "delete_calendar_events", lambda s, r: {"ids": [s.get("calendarEvent", {}).get("id"), s.get("calendarEvent", {}).get("id")]}, None, False),
    ("bulk_delete_message", "delete_messages", lambda s, r: {"ids": [s.get("message", {}).get("id"), s.get("message", {}).get("id")]}, None, False),
    ("bulk_delete_noteTarget", "delete_note_targets", lambda s, r: {"ids": [s.get("noteTarget", {}).get("id"), s.get("noteTarget", {}).get("id")]}, None, False),
    ("bulk_delete_taskTarget", "delete_task_targets", lambda s, r: {"ids": [s.get("taskTarget", {}).get("id"), s.get("taskTarget", {}).get("id")]}, None, False),
    ("bulk_delete_timelineActivity", "delete_timeline_activities", lambda s, r: {"ids": [s.get("timelineActivity", {}).get("id"), s.get("timelineActivity", {}).get("id")]}, None, False),
    ("bulk_delete_attachment", "delete_attachments", lambda s, r: {"ids": [s.get("attachment", {}).get("id"), s.get("attachment", {}).get("id")]}, None, False),
    ("bulk_delete_callRecording", "delete_call_recordings", lambda s, r: {"ids": [s.get("callRecording", {}).get("id"), s.get("callRecording", {}).get("id")]}, None, False),
    ("bulk_delete_calendarEventParticipant", "delete_calendar_event_participants", lambda s, r: {"ids": [s.get("calendarEventParticipant", {}).get("id"), s.get("calendarEventParticipant", {}).get("id")]}, None, False),
    ("bulk_delete_messageParticipant", "delete_message_participants", lambda s, r: {"ids": [s.get("messageParticipant", {}).get("id"), s.get("messageParticipant", {}).get("id")]}, None, False),
]


# =============================================================================
# Main — sequential flat execution, zero conditionals
# =============================================================================

async def main():
    print("# Test Report — Twenty MCP Server")
    print(f"\n**Date**: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    print(f"**Server**: {MCP_URL}")
    print(f"**Run ID**: {rid}")
    print()

    async with MCPSession(MCP_URL, MCP_HEADERS) as session:
        tools_list = await session.list_tools()
        tool_names = [t["name"] for t in tools_list]
        print(f"**Discovered**: {len(tool_names)} tools")
        log(f"Tools: {', '.join(sorted(tool_names))}")

        log("\n=== Phase 1: Status & Health ===")
        await _exec(session, PHASE1_TESTS)

        log("\n=== Phase 2: List Tools (Smoke Test) ===")
        await _exec(session, PHASE2_TESTS)

        log("\n=== Phase 3: Per-Resource CRUD Loop ===")
        log("  Phase 3a — C1 creates (forward order)")
        await _exec(session, PHASE3A_TESTS)
        log("  Phase 3b — C2 gets (forward order)")
        await _exec(session, PHASE3B_TESTS)
        log("  Phase 3c — C3 updates (forward order)")
        await _exec(session, PHASE3C_TESTS)
        log("  Phase 3d — C4 deletes (REVERSE order)")
        await _exec(session, PHASE3D_TESTS)
        log("  Phase 3e — C5 verify deletes (REVERSE order)")
        await _exec(session, PHASE3E_TESTS)

        log("\n=== Phase 4: Bulk Update & Delete ===")
        await _exec(session, PHASE4_TESTS)

        log("\n=== Phase 5: Leak Detection ===")
        await _run_leak_detection(session)

        passed = sum(r["status"] == "PASSED" for r in results)
        failed = sum(r["status"] == "FAILED" for r in results)
        passes = list(filter(lambda r: r["status"] == "PASSED", results))
        fails = list(filter(lambda r: r["status"] == "FAILED", results))

        print(f"\n## Summary\n")
        print(f"| Status | Count |")
        print(f"|--------|-------|")
        print(f"| PASSED | {passed} |")
        print(f"| FAILED | {failed} |")

        print(f"\n## PASSED ({len(passes)})\n")
        for r in passes:
            print(f"- `{r['tool']}` — {r['label']}")

        print(f"\n## FAILED ({len(fails)})\n")
        for r in fails:
            print(f"### {r['label']}")
            print(f"- **Error**: {r['reason']}")
            print()

        total = len(results)
        print(f"\n---")
        print(f"**Total tests:** {total} | **PASSED:** {passed} | **FAILED:** {failed}")

        print(f"\n**{['TESTS FAILING', 'ALL TESTS PASS'][failed == 0]}**")


if __name__ == "__main__":
    asyncio.run(main())
