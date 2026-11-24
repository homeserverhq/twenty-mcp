# Twenty MCP Server

This repository contains a Model Context Protocol (MCP) server that acts
as a secure, multi-tenant proxy between an AI Assistant and the Twenty
backend API. It exposes **115 MCP tools** covering 17 resource domains
with CRUD operations, cursor pagination, and relationship management.

## ✨ Features

- **🔑 Identity Passthrough** — Extracts the `Authorization: Bearer <token>`
  header from incoming HTTP requests and forwards it to the Twenty API
  without server-side authentication.
- **👥 Multi-Tenancy** — Uses Python `contextvars` to maintain per-request
  token isolation, ensuring all AI-driven actions are scoped to the
  authenticated workspace and key.
- **📊 Full Twenty Coverage** — 115 tools mapped to Twenty REST API endpoints
  across 17 resource domains.
- **⚡ TOON Optimization** — Bulk list responses are automatically compressed
  using TOON (Token-Optimized Object Notation) to reduce token consumption
  and maximize context window efficiency.
- **🚀 Efficient Gets** — GET responses return only commonly used fields by
  default. Full objects are available via an `include_all_fields` flag.
- **📄 Cursor Pagination** — Every `list_*` tool accepts `limit` (1–200) and
  `starting_after`, and returns `total_count` plus `page_info`.
- **🕒 ISO Dates** — Date/time inputs accept ISO 8601 with `Z` or an offset,
  including fractional seconds; payloads are normalized to UTC.
- **🧪 Comprehensive Testing** — 132 smoke tests plus a 640-check semantic
  audit with full tool coverage.
- **🏷️ Tool Annotations** — All tools expose standard MCP ToolAnnotations
  hints (readOnlyHint, destructiveHint, idempotentHint, openWorldHint).
  The tags field carries grouping metadata (basic/primary/advanced + twenty).

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TWENTY_BASE_URL` | Yes | Docker-internal URL of the Twenty API (e.g. `http://twenty-app:3000`). |
| `MCP_SERVER_PORT` | Yes | Port number the MCP server listens on |
| `ALLOW_ALL_AGGREGATE` | No | When `true`, aggregate listing tools honor the `include_all_fields` parameter. When `false` (default), the parameter is forced to `False` for aggregate list operations; list-tool docstrings state this explicitly. |
| `IS_STATEFUL` | No | When `true`, uses stateful Streamable HTTP with session tracking. When `false` (default), uses stateless mode. |

## 📦 Installation & Local Development

1. Ensure you have Python 3.12+ installed.
2. Install dependencies:
    ```bash
    pip install fastmcp httpx pydantic uvicorn toon-mcp-server
    ```
3. Run the server:
    ```bash
    export TWENTY_BASE_URL=http://localhost:8279
    export MCP_SERVER_PORT=80
    python -m src.main
    ```

## 🐳 Docker Deployment

Build and run the server using Docker:

```bash
docker build -t twenty-mcp:latest .
docker run -d --name twenty-mcp \
    -e TWENTY_BASE_URL="http://twenty-app:3000" \
    -e MCP_SERVER_PORT=80 \
    -e ALLOW_ALL_AGGREGATE=false \
    -e IS_STATEFUL=false \
    twenty-mcp:latest

The MCP server serves at `http://twenty-mcp:80/mcp` (Streamable HTTP).
```

## ⚠️ Important Notes

- **📋 `include_all_fields`** — The `include_all_fields` parameter (available
  on all `get_*` and `list_*` tools) controls whether all available fields
  are included in responses. Defaults to `False` for performance; set to
  `True` only when additional fields are needed.
- **🔒 `ALLOW_ALL_AGGREGATE`** — A deliberate hard gate for aggregate
  list calls. When `false` (default), `list_*` tools return only the common
  field set even if the caller passes `include_all_fields=true`. This is
  intentional: it prevents a single aggregate call from blowing up the model
  context. Single-record `get_*` tools always honor `include_all_fields`.
  The list-tool docstrings state this behavior explicitly.
- **🕒 Dates** — Pass ISO 8601 strings with an explicit offset or `Z`, e.g.
  `2026-06-22T15:00:00-04:00`. Naive datetimes, date-only values, and epoch
  integers are rejected.
- **✍️ Updates** — Every `update_*` call must include at least one mutable
  field; an id-only update is rejected instead of silently doing nothing.
- **🚫 Empty bulk calls** — Bulk update/delete reject an empty `ids` list.
- **⚡ TOON Compression** — All bulk list responses are automatically
  compressed using TOON to reduce token consumption by 30–60%.
- **📝 Required Fields & Defaults** — Each `create_*` tool requires specific
  key fields. All other fields default to empty strings or reasonable values.
  The `createdBy` field is automatically populated by the backend API.

## 🧪 Semantic Audit

The audit suite lives in `src/audit/` and is independent of the server code.
It speaks JSON-RPC/SSE to a running server and covers every tool in
`tools/list`.

```bash
# Run inside the server container
export API_KEY="<twenty-api-key>"
python -m src.audit.selftest
python -m src.audit.runner --l0 --quiet   # schema-only; no API key required
python -m src.audit.runner --all --quiet
```

Useful options:

```bash
python -m src.audit.runner --list-domains
python -m src.audit.runner --domain resources,pagination
python -m src.audit.runner --all --report docs/tool-audit.md \
    --json docs/tool-audit.json
```

`--all` enforces coverage: every live tool must be declared and called, and
the residue scan must find zero `MCPAudit-<run>` fixtures. The audit uses the
same workspace-scoped bearer token as a normal client; set
`AUDIT_SECONDARY_API_KEY` to add a second key for same-workspace visibility
checks.

See `docs/tool-audit.md`, `docs/tool-audit.json`, and `docs/audit-notes.md`
for the latest run and known limitations.

### Known backend limitations

- **`list_messages`** — Twenty's message list joins
  `messageChannelMessageAssociation`. This workspace has no message channels,
  so the backend returns `totalCount > 0` with zero rows. `get_message_by_id`
  still works. The list tool now returns a `warning` when the backend reports
  more rows than it returns.
- **Calendar events created by this MCP** — Twenty's calendar-event list joins
  `calendarChannelEventAssociation`. Events created through `create_calendar_event`
  have no association, so they are visible through `get_calendar_event_by_id`
  but omitted from `list_calendar_events`. The list tool returns a `warning`
  for this count mismatch.

## 🛠️ API Tool Mapping

The server implements 115 MCP tools organized into the following categories:

### 🏢 Company (7 tools)

- `list_companies` — List company records
- `get_company_by_id` — Get a single company by ID
- `create_company` — Create a new company record
- `update_company` — Update an existing company record
- `update_companies` — Bulk update company records by IDs
- `delete_company_by_id` — Delete a company by ID
- `delete_companies` — Bulk delete companies by IDs

### 🧑 Person (7 tools)

- `list_people` — List person records
- `get_person_by_id` — Get a single person by ID
- `create_person` — Create a new person record
- `update_person` — Update an existing person record
- `update_people` — Bulk update person records by IDs
- `delete_person_by_id` — Delete a person by ID
- `delete_people` — Bulk delete people by IDs

### 💰 Opportunity (7 tools)

- `list_opportunities` — List opportunity records
- `get_opportunity_by_id` — Get a single opportunity by ID
- `create_opportunity` — Create a new opportunity record
- `update_opportunity` — Update an existing opportunity record
- `update_opportunities` — Bulk update opportunity records by IDs
- `delete_opportunity_by_id` — Delete an opportunity by ID
- `delete_opportunities` — Bulk delete opportunities by IDs

### 📓 Note (7 tools)

- `list_notes` — List note records
- `get_note_by_id` — Get a single note by ID
- `create_note` — Create a new note record
- `update_note` — Update an existing note record
- `update_notes` — Bulk update note records by IDs
- `delete_note_by_id` — Delete a note by ID
- `delete_notes` — Bulk delete notes by IDs

### ✅ Task (7 tools)

- `list_tasks` — List task records
- `get_task_by_id` — Get a single task by ID
- `create_task` — Create a new task record
- `update_task` — Update an existing task record
- `update_tasks` — Bulk update task records by IDs
- `delete_task_by_id` — Delete a task by ID
- `delete_tasks` — Bulk delete tasks by IDs

### 🌀 Workflow (5 tools)

- `list_workflows` — List workflow records
- `get_workflow_by_id` — Get a single workflow by ID
- `create_workflow` — Create a new workflow record
- `update_workflow` — Update an existing workflow record
- `delete_workflow_by_id` — Delete a workflow by ID

### 🆔 WorkspaceMember (4 tools)

- `list_workspace_members` — List workspace member records
- `get_workspace_member_by_id` — Get a single workspace member by ID
- `update_workspace_member` — Update an existing workspace member record
- `update_workspace_members` — Bulk update workspace member records by IDs

### 📎 Attachment (7 tools)

- `list_attachments` — List attachment records
- `get_attachment_by_id` — Get a single attachment by ID
- `create_attachment` — Create a new attachment record
- `update_attachment` — Update an existing attachment record
- `update_attachments` — Bulk update attachment records by IDs
- `delete_attachment_by_id` — Delete an attachment by ID
- `delete_attachments` — Bulk delete attachments by IDs

### 🔖 NoteTarget (7 tools)

- `list_note_targets` — List note target records
- `get_note_target_by_id` — Get a single note target by ID
- `create_note_target` — Create a new note target record
- `update_note_target` — Update an existing note target record
- `update_note_targets` — Bulk update note target records by IDs
- `delete_note_target_by_id` — Delete a note target by ID
- `delete_note_targets` — Bulk delete note targets by IDs

### 🎯 TaskTarget (7 tools)

- `list_task_targets` — List task target records
- `get_task_target_by_id` — Get a single task target by ID
- `create_task_target` — Create a new task target record
- `update_task_target` — Update an existing task target record
- `update_task_targets` — Bulk update task target records by IDs
- `delete_task_target_by_id` — Delete a task target by ID
- `delete_task_targets` — Bulk delete task targets by IDs

### ⏰ TimelineActivity (7 tools)

- `list_timeline_activities` — List timeline activity records
- `get_timeline_activity_by_id` — Get a single timeline activity by ID
- `create_timeline_activity` — Create a new timeline activity record
- `update_timeline_activity` — Update an existing timeline activity record
- `update_timeline_activities` — Bulk update timeline activity records by IDs
- `delete_timeline_activity_by_id` — Delete a timeline activity by ID
- `delete_timeline_activities` — Bulk delete timeline activities by IDs

### 📅 CalendarEvent (7 tools)

- `list_calendar_events` — List calendar event records
- `get_calendar_event_by_id` — Get a single calendar event by ID
- `create_calendar_event` — Create a new calendar event record
- `update_calendar_event` — Update an existing calendar event record
- `update_calendar_events` — Bulk update calendar event records by IDs
- `delete_calendar_event_by_id` — Delete a calendar event by ID
- `delete_calendar_events` — Bulk delete calendar events by IDs

### 🙋 CalendarEventParticipant (7 tools)

- `list_calendar_event_participants` — List calendar event participant records
- `get_calendar_event_participant_by_id` — Get a single calendar event participant by ID
- `create_calendar_event_participant` — Create a new calendar event participant record
- `update_calendar_event_participant` — Update an existing calendar event participant record
- `update_calendar_event_participants` — Bulk update calendar event participant records by IDs
- `delete_calendar_event_participant_by_id` — Delete a calendar event participant by ID
- `delete_calendar_event_participants` — Bulk delete calendar event participants by IDs

### ✉️ Message (7 tools)

- `list_messages` — List message records
- `get_message_by_id` — Get a single message by ID
- `create_message` — Create a new message record
- `update_message` — Update an existing message record
- `update_messages` — Bulk update message records by IDs
- `delete_message_by_id` — Delete a message by ID
- `delete_messages` — Bulk delete messages by IDs

### 📬 MessageThread (7 tools)

- `list_message_threads` — List message thread records
- `get_message_thread_by_id` — Get a single message thread by ID
- `create_message_thread` — Create a new message thread record
- `update_message_thread` — Update an existing message thread record
- `update_message_threads` — Bulk update message thread records by IDs
- `delete_message_thread_by_id` — Delete a message thread by ID
- `delete_message_threads` — Bulk delete message threads by IDs

### 🗣️ MessageParticipant (7 tools)

- `list_message_participants` — List message participant records
- `get_message_participant_by_id` — Get a single message participant by ID
- `create_message_participant` — Create a new message participant record
- `update_message_participant` — Update an existing message participant record
- `update_message_participants` — Bulk update message participant records by IDs
- `delete_message_participant_by_id` — Delete a message participant by ID
- `delete_message_participants` — Bulk delete message participants by IDs

### 🎙️ CallRecording (7 tools)

- `list_call_recordings` — List call recording records
- `get_call_recording_by_id` — Get a single call recording by ID
- `create_call_recording` — Create a new call recording record
- `update_call_recording` — Update an existing call recording record
- `update_call_recordings` — Bulk update call recording records by IDs
- `delete_call_recording_by_id` — Delete a call recording by ID
- `delete_call_recordings` — Bulk delete call recordings by IDs

### 🔧 Domain-Specific Tools (1 tool)

- `check_server_status` — Check connectivity and authentication against the Twenty backend API
