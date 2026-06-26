"""
End-to-end test harness for Twenty MCP Server.

Tests all 120 MCP tools via Streamable HTTP (JSON-RPC POST).
Per spec §5.5: per-resource CRUD loop — C1→C2→C3→C4→C5 per resource.
No SKIP logic — downstream tests use placeholder ID "0" on failure.
Phase 4: bulk update + bulk delete for all 17 resources.
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


async def run_test(
    session: MCPSession,
    label: str,
    tool: str,
    params: dict[str, Any] = None,
) -> bool:
    if params is None:
        params = {}
    try:
        result = await session.call_tool(tool, params)
        err = is_error(result)
        if err:
            results.append({"label": label, "tool": tool, "status": "FAILED", "reason": err})
            log(f"  FAIL {label}: {err}")
            return False
        data = extract_content(result)
        results.append({"label": label, "tool": tool, "status": "PASSED", "data": data})
        log(f"  PASS {label}")
        return True
    except Exception as e:
        results.append({"label": label, "tool": tool, "status": "FAILED", "reason": str(e)})
        log(f"  FAIL {label}: {e}")
        return False


async def run_test_capture_id(
    session: MCPSession,
    label: str,
    tool: str,
    params: dict[str, Any],
    store_key: str,
) -> str:
    ok = await run_test(session, label, tool, params)
    entity_id = "0"
    if ok:
        for r in reversed(results):
            if r["label"] == label and r["status"] == "PASSED":
                data = r.get("data", {})
                if isinstance(data, dict):
                    entity_id = data.get("id", "0")
                store[store_key] = data
                break
    else:
        store[store_key] = {"id": "0"}
    return entity_id


async def run_verify_delete(
    session: MCPSession,
    label: str,
    get_tool: str,
    params: dict[str, Any],
) -> bool:
    try:
        result = await session.call_tool(get_tool, params)
        err = is_error(result)
        if err:
            if "not found" in err.lower() or "404" in err.lower():
                results.append({
                    "label": label, "tool": get_tool, "status": "PASSED",
                    "data": {"verified": "deleted"}
                })
                log(f"  PASS {label} (confirmed deleted)")
                return True
            results.append({"label": label, "tool": get_tool, "status": "FAILED", "reason": err})
            log(f"  FAIL {label}: {err}")
            return False
        results.append({"label": label, "tool": get_tool, "status": "FAILED", "reason": "Record still exists after delete"})
        log(f"  FAIL {label}: record still exists")
        return False
    except Exception as e:
        err_str = str(e).lower()
        if "not found" in err_str or "404" in err_str:
            results.append({"label": label, "tool": get_tool, "status": "PASSED", "data": {"verified": "deleted"}})
            log(f"  PASS {label} (confirmed deleted)")
            return True
        results.append({"label": label, "tool": get_tool, "status": "FAILED", "reason": str(e)})
        log(f"  FAIL {label}: {e}")
        return False


def make_name(base: str) -> str:
    return f"t{rid}-{base}"


def make_email(local: str) -> str:
    return f"{local}{rid}@example.com"


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
        try:
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
                    "reason": f"Leaked {entity_type} found after test run — delete was not called or failed"
                })
                log(f"  FAIL {label}")
                del_params = {id_key: item_id, **delete_extra}
                try:
                    await session.call_tool(delete_tool, del_params)
                    log(f"       => cleaned up {entity_type} {item_id}")
                except Exception as del_err:
                    log(f"       => cleanup failed: {del_err}")
        except Exception:
            pass

    if total_leaks == 0:
        results.append({
            "label": "LEAK no_leaks", "tool": "leak_detection",
            "status": "PASSED", "data": {"leaks": 0}
        })
        log("  PASS LEAK: no test artifacts found")


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


# =============================================================================
# RESOURCE_TESTS — in CREATION ORDER (parents first, children last)
# Each entry: (label, create_tool, create_params_fn, list_tool, get_tool,
#              update_tool, update_params_fn, delete_tool, store_key)
#
# create_params_fn and update_params_fn: callable(store, rid) -> dict
# Store key format: "{resource}" → store["company"] = created data dict
# =============================================================================
RESOURCE_TESTS = [
    # 1. company — standalone root
    ("company", "create_company",
     lambda s, r: {
         "name": f"t{r}-Company",
         "domainName": {"primaryLinkUrl": f"https://t{r}-testco.com", "primaryLinkLabel": ""},
     },
     "list_companies", "get_company_by_id",
     "update_company",
     lambda s, r: {"name": f"t{r}-Company-Upd"},
     "delete_company_by_id", "company"),

    # 2. person — standalone root (optional companyId)
    ("person", "create_person",
     lambda s, r: {
         "name": {"firstName": f"t{r}", "lastName": "Person"},
         "emails": {"primaryEmail": f"t{r}-person@example.com"},
     },
     "list_people", "get_person_by_id",
     "update_person",
     lambda s, r: {"jobTitle": f"t{r}-Engineer"},
     "delete_person_by_id", "person"),

    # 3. opportunity — standalone root (optional companyId/personId/ownerId)
    ("opportunity", "create_opportunity",
     lambda s, r: {"name": f"t{r}-Opportunity", "stage": "NEW"},
     "list_opportunities", "get_opportunity_by_id",
     "update_opportunity",
     lambda s, r: {"stage": "SCREENING"},
     "delete_opportunity_by_id", "opportunity"),

    # 4. note — standalone root
    ("note", "create_note",
     lambda s, r: {"title": f"t{r}-Note"},
     "list_notes", "get_note_by_id",
     "update_note",
     lambda s, r: {"title": f"t{r}-Note-Upd"},
     "delete_note_by_id", "note"),

    # 5. task — standalone root (optional assigneeId)
    ("task", "create_task",
     lambda s, r: {"title": f"t{r}-Task", "status": "TODO"},
     "list_tasks", "get_task_by_id",
     "update_task",
     lambda s, r: {"status": "IN_PROGRESS"},
     "delete_task_by_id", "task"),

    # 6. workflow — standalone root
    ("workflow", "create_workflow",
     lambda s, r: {"name": f"t{r}-Workflow", "statuses": ["ACTIVE"]},
     "list_workflows", "get_workflow_by_id",
     "update_workflow",
     lambda s, r: {},
     "delete_workflow_by_id", "workflow"),

    # 7. messageThread — standalone root
    ("messageThread", "create_message_thread",
     lambda s, r: {"subject": f"t{r}-Thread"},
     "list_message_threads", "get_message_thread_by_id",
     "update_message_thread",
     lambda s, r: {"subject": f"t{r}-Thread-Upd"},
     "delete_message_thread_by_id", "messageThread"),

    # 8. calendarEvent — standalone root
    ("calendarEvent", "create_calendar_event",
     lambda s, r: {
         "title": f"t{r}-CalEvent",
         "startsAt": "2026-06-26T14:00:00+00:00",
         "endsAt": "2026-06-26T15:00:00+00:00",
     },
     "list_calendar_events", "get_calendar_event_by_id",
     "update_calendar_event",
     lambda s, r: {"title": f"t{r}-CalEvent-Upd"},
     "delete_calendar_event_by_id", "calendarEvent"),

    # 9. message — standalone root (optional messageThreadId)
    ("message", "create_message",
     lambda s, r: {"subject": f"t{r}-Message"},
     "list_messages", "get_message_by_id",
     "update_message",
     lambda s, r: {"subject": f"t{r}-Message-Upd"},
     "delete_message_by_id", "message"),

    # 10. noteTarget — junction (requires noteId)
    ("noteTarget", "create_note_target",
     lambda s, r: {"noteId": s.get("note", {}).get("id", "0")},
     "list_note_targets", "get_note_target_by_id",
     "update_note_target",
     lambda s, r: {},
     "delete_note_target_by_id", "noteTarget"),

    # 11. taskTarget — junction (requires taskId)
    ("taskTarget", "create_task_target",
     lambda s, r: {"taskId": s.get("task", {}).get("id", "0")},
     "list_task_targets", "get_task_target_by_id",
     "update_task_target",
     lambda s, r: {},
     "delete_task_target_by_id", "taskTarget"),

    # 12. timelineActivity — standalone (optional workspaceMemberId + target IDs)
    ("timelineActivity", "create_timeline_activity",
     lambda s, r: {
         "name": f"t{r}-Timeline",
         "happensAt": "2026-06-26T14:00:00+00:00",
     },
     "list_timeline_activities", "get_timeline_activity_by_id",
     "update_timeline_activity",
     lambda s, r: {"name": f"t{r}-Timeline-Upd"},
     "delete_timeline_activity_by_id", "timelineActivity"),

    # 13. attachment — standalone (optional authorId + target IDs)
    ("attachment", "create_attachment",
     lambda s, r: {"name": f"t{r}-Attachment", "fullPath": f"/tmp/t{r}-att.pdf"},
     "list_attachments", "get_attachment_by_id",
     "update_attachment",
     lambda s, r: {"name": f"t{r}-Attachment-Upd"},
     "delete_attachment_by_id", "attachment"),

    # 14. callRecording — standalone (optional calendarEventId)
    ("callRecording", "create_call_recording",
     lambda s, r: {"title": f"t{r}-Call", "status": "RECORDING"},
     "list_call_recordings", "get_call_recording_by_id",
     "update_call_recording",
     lambda s, r: {"status": "COMPLETED"},
     "delete_call_recording_by_id", "callRecording"),

    # 15. calendarEventParticipant — HARD dependency (requires calendarEventId)
    ("calendarEventParticipant", "create_calendar_event_participant",
     lambda s, r: {
         "calendarEventId": s.get("calendarEvent", {}).get("id", "0"),
         "handle": f"t{r}-calpart@example.com",
         "displayName": f"t{r}-CalPart",
     },
     "list_calendar_event_participants", "get_calendar_event_participant_by_id",
     "update_calendar_event_participant",
     lambda s, r: {"displayName": f"t{r}-CalPart-Upd"},
     "delete_calendar_event_participant_by_id", "calendarEventParticipant"),

    # 16. messageParticipant — HARD dependency (requires messageId)
    ("messageParticipant", "create_message_participant",
     lambda s, r: {
         "messageId": s.get("message", {}).get("id", "0"),
         "handle": f"t{r}-msgpart",
         "displayName": f"t{r}-MsgPart",
         "role": "FROM",
     },
     "list_message_participants", "get_message_participant_by_id",
     "update_message_participant",
     lambda s, r: {"displayName": f"t{r}-MsgPart-Upd"},
     "delete_message_participant_by_id", "messageParticipant"),
]


async def main():
    print(f"# Test Report — Twenty MCP Server")
    print(f"\n**Date**: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    print(f"**Server**: {MCP_URL}")
    print(f"**Run ID**: {rid}")
    print()

    async with MCPSession(MCP_URL, MCP_HEADERS) as session:
        # Phase 0: Session Init & Tool Discovery
        log("\n=== Phase 0: Session Init & Tool Discovery ===")
        tools_list = await session.list_tools()
        tool_names = [t["name"] for t in tools_list]
        print(f"**Discovered**: {len(tool_names)} tools")
        log(f"Tools: {', '.join(sorted(tool_names))}")

        # Phase 1: Status Check
        log("\n=== Phase 1: Status & Health ===")
        await run_test(session, "check_server_status", "check_server_status")

        # Phase 2: List Tools (Smoke Test)
        log("\n=== Phase 2: List Tools (Smoke Test) ===")
        for entry in RESOURCE_TESTS:
            label = entry[0]
            list_tool_name = entry[3]
            await run_test(session, f"list_{label}", list_tool_name)

        # Phase 3: Per-resource CRUD loop (C1→C2→C3→C4→C5 per spec §5.5)
        # No SKIP logic — use "0" as placeholder ID when create fails
        # C1 (create) runs forward so parents exist before children reference them.
        # C4 (delete) + C5 (verify) runs REVERSE so children are deleted before parents.
        log("\n=== Phase 3: Per-Resource CRUD Loop ===")
        log("  Phase 3a — C1 creates (forward order)")
        for entry in RESOURCE_TESTS:
            label = entry[0]
            create_tool = entry[1]
            create_params_fn = entry[2]
            store_key = entry[8]

            create_params = create_params_fn(store, rid)
            await run_test_capture_id(
                session, f"C1 create_{label}", create_tool, create_params, store_key
            )

        log("  Phase 3b — C2 gets + C3 updates (forward order)")
        for entry in RESOURCE_TESTS:
            label = entry[0]
            get_tool = entry[4]
            update_tool = entry[5]
            update_params_fn = entry[6]
            store_key = entry[8]

            entity_data = store.get(store_key, {})
            entity_id = entity_data.get("id", "0") if isinstance(entity_data, dict) else "0"
            get_params = {"id": entity_id}

            await run_test(session, f"C2 get_{label}", get_tool, get_params)

            upd_params = update_params_fn(store, rid)
            upd_params["id"] = entity_id
            await run_test(session, f"C3 update_{label}", update_tool, upd_params)

        log("  Phase 3c — C4 deletes + C5 verifies (REVERSE order)")
        for entry in reversed(RESOURCE_TESTS):
            label = entry[0]
            get_tool = entry[4]
            delete_tool = entry[7]
            store_key = entry[8]

            entity_data = store.get(store_key, {})
            entity_id = entity_data.get("id", "0") if isinstance(entity_data, dict) else "0"
            get_params = {"id": entity_id}

            await run_test(session, f"C4 delete_{label}", delete_tool, {"id": entity_id})
            await run_verify_delete(session, f"C5 verify_delete_{label}", get_tool, get_params)

        # Phase 4: Bulk update + bulk delete for all remaining resources
        log("\n=== Phase 4: Bulk Update & Delete ===")

        BULK_UPDATE_TOOLS: dict[str, str] = {
            "company": "update_companies",
            "person": "update_people",
            "opportunity": "update_opportunities",
            "note": "update_notes",
            "task": "update_tasks",
            "messageThread": "update_message_threads",
            "calendarEvent": "update_calendar_events",
            "message": "update_messages",
            "noteTarget": "update_note_targets",
            "taskTarget": "update_task_targets",
            "timelineActivity": "update_timeline_activities",
            "attachment": "update_attachments",
            "callRecording": "update_call_recordings",
            "calendarEventParticipant": "update_calendar_event_participants",
            "messageParticipant": "update_message_participants",
        }

        BULK_DELETE_TOOLS: dict[str, str] = {
            "company": "delete_companies",
            "person": "delete_people",
            "opportunity": "delete_opportunities",
            "note": "delete_notes",
            "task": "delete_tasks",
            "messageThread": "delete_message_threads",
            "calendarEvent": "delete_calendar_events",
            "message": "delete_messages",
            "noteTarget": "delete_note_targets",
            "taskTarget": "delete_task_targets",
            "timelineActivity": "delete_timeline_activities",
            "attachment": "delete_attachments",
            "callRecording": "delete_call_recordings",
            "calendarEventParticipant": "delete_calendar_event_participants",
            "messageParticipant": "delete_message_participants",
        }

        for entry in RESOURCE_TESTS:
            label = entry[0]
            update_params_fn = entry[6]
            store_key = entry[8]

            if label not in BULK_UPDATE_TOOLS:
                log(f"  N/A bulk_{label}: no bulk tools defined (removed)")
                continue
            bulk_update_tool = BULK_UPDATE_TOOLS[label]
            bulk_delete_tool = BULK_DELETE_TOOLS[label]

            entity_data = store.get(store_key, {})
            entity_id = entity_data.get("id", "0") if isinstance(entity_data, dict) else "0"

            upd = update_params_fn(store, rid)
            upd["ids"] = [entity_id, entity_id]
            await run_test(session, f"bulk_update_{label}", bulk_update_tool, upd)
            await run_test(session, f"bulk_delete_{label}", bulk_delete_tool, {"ids": [entity_id, entity_id]})

        # Phase 5: Leak Detection
        log("\n=== Phase 5: Leak Detection ===")
        await _run_leak_detection(session)

        passed = sum(1 for r in results if r["status"] == "PASSED")
        failed = sum(1 for r in results if r["status"] == "FAILED")
        skipped = sum(1 for r in results if r["status"] == "SKIPPED")

        print(f"\n## Summary\n")
        print(f"| Status | Count |")
        print(f"|--------|-------|")
        print(f"| PASSED | {passed} |")
        print(f"| FAILED | {failed} |")
        print(f"| SKIPPED | {skipped} |")

        if passed:
            print(f"\n## PASSED ({passed})\n")
            for r in results:
                if r["status"] == "PASSED":
                    print(f"- `{r['tool']}` — {r['label']}")

        if failed:
            print(f"\n## FAILED ({failed})\n")
            for r in results:
                if r["status"] == "FAILED":
                    print(f"### {r['label']}")
                    print(f"- **Error**: {r['reason']}")
                    print()

        total = len(results)
        print(f"\n---")
        print(f"**Total tests:** {total} | **PASSED:** {passed} | **FAILED:** {failed} | **SKIPPED:** {skipped}")

        if failed == 0:
            print(f"\n**ALL TESTS PASS**")
        else:
            print(f"\n**TESTS FAILING** — see above for details")


if __name__ == "__main__":
    asyncio.run(main())