# Twenty MCP Multitenant Proxy Server

This repository contains a Model Context Protocol (MCP) server that acts as a secure, multi-tenant proxy between an AI Assistant and the Twenty CRM backend API. It exposes **120 MCP tools** covering 17 resource domains with full CRUD operations, plus server health monitoring.

## ✨ Features

- **🔑 Identity Passthrough** — Extracts the `Authorization: Bearer <token>` header from incoming HTTP requests and forwards it to the Twenty API without server-side authentication.
- **👥 Multi-Tenancy** — Uses Python `contextvars` to maintain thread-safe user identity isolation, ensuring all AI-driven actions are scoped to the authenticated user's permissions.
- **📊 Full Twenty Coverage** — 120 tools mapped to Twenty REST API endpoints across 17 resource domains.
- **⚡ TOON Optimization** — Bulk list responses are automatically compressed using TOON (Token-Optimized Object Notation) to reduce token consumption and maximize context window efficiency.
- **⚡ Efficient Gets** — GET responses return only commonly used fields by default. Full objects are available via an `include_all_fields` flag.
- **🔒 Hard Destroy Deletes** — Delete operations permanently remove records from the backend.
- **🧪 Comprehensive Testing** — 120+ automated tests covering all tool domains via the test runner pipeline.

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `Twenty_BASE_URL` | Yes | Docker-internal URL of the Twenty API (e.g. `http://twenty-app:3000/rest/`). |
| `MCP_SERVER_PORT` | Yes | Port number the MCP server listens on. |
| `ALLOW_ALL_AGGREGATE` | No | When `true`, aggregate listing tools honor the `include_all_fields` parameter. When `false` (default), the parameter is silently forced to `False` for aggregate list operations. |

## 📦 Installation & Local Development

1. Ensure you have Python 3.12+ installed.
2. Install dependencies:
   ```bash
   pip install fastmcp httpx pydantic uvicorn toon-mcp-server
   ```
3. Run the server:
   ```bash
   export Twenty_BASE_URL=http://localhost:8279/rest/
   export MCP_SERVER_PORT=6375
   python -m src.main
   ```

## 🐳 Docker Deployment

Build and run the server using Docker:

```bash
docker build -t twenty-mcp .
docker run -d --name twenty-mcp --network dock-ext \
    -p 6375:6375 \
    -e Twenty_BASE_URL="http://twenty-app:3000/rest/" \
    -e MCP_SERVER_PORT=6375 \
    -e ALLOW_ALL_AGGREGATE=true \
    twenty-mcp
```

The MCP server serves at `http://twenty-mcp:6375/mcp` (Streamable HTTP).

## ⚠️ Important Notes

- **📋 `include_all_fields`** — The `include_all_fields` parameter (available on all `get_*` and `list_*` tools) controls whether all available fields are included in responses. Defaults to `False` for performance; set to `True` only when additional fields are needed.
- **⚡ TOON Compression** — All bulk list responses are automatically compressed using TOON (Token-Optimized Object Notation) to reduce token consumption by 30-60%.
- **📝 Required Fields & Defaults** — Each `create_*` tool requires specific key fields (e.g. `name` for most resources). All other fields default to empty strings or reasonable values. The `createdBy` field is automatically populated by the backend API.
- **🗑️ Hard Destroy Deletes** — All delete operations permanently remove records. There is no soft-delete or trash recovery.
- **🗂️ Composite Fields** — Fields like `domainName`, `address`, `name`, `amount`, `emails` are composite objects. They are accepted as JSON strings in create/update tools and parsed internally before sending to the API.

## 🛠️ API Tool Mapping

The server implements 120 MCP tools organized across 17 resource domains:

### 🏢 Company (7 tools)
- `list_companies` — List all company records
- `get_company_by_id` — Get a single company by ID
- `create_company` — Create a new company record
- `update_company` — Update an existing company record
- `update_companies` — Bulk update company records by IDs
- `delete_company_by_id` — Delete a company by ID (hard destroy)
- `delete_companies` — Bulk delete companies by IDs (hard destroy)

### 👤 Person (7 tools)
- `list_people` — List all person records
- `get_person_by_id` — Get a single person by ID
- `create_person` — Create a new person record
- `update_person` — Update an existing person record
- `update_people` — Bulk update person records by IDs
- `delete_person_by_id` — Delete a person by ID (hard destroy)
- `delete_people` — Bulk delete people by IDs (hard destroy)

### 💰 Opportunity (7 tools)
- `list_opportunities` — List all opportunity records
- `get_opportunity_by_id` — Get a single opportunity by ID
- `create_opportunity` — Create a new opportunity record
- `update_opportunity` — Update an existing opportunity record
- `update_opportunities` — Bulk update opportunity records by IDs
- `delete_opportunity_by_id` — Delete an opportunity by ID (hard destroy)
- `delete_opportunities` — Bulk delete opportunities by IDs (hard destroy)

### 📝 Note (7 tools)
- `list_notes` — List all note records
- `get_note_by_id` — Get a single note by ID
- `create_note` — Create a new note record
- `update_note` — Update an existing note record
- `update_notes` — Bulk update note records by IDs
- `delete_note_by_id` — Delete a note by ID (hard destroy)
- `delete_notes` — Bulk delete notes by IDs (hard destroy)

### ✅ Task (7 tools)
- `list_tasks` — List all task records
- `get_task_by_id` — Get a single task by ID
- `create_task` — Create a new task record
- `update_task` — Update an existing task record
- `update_tasks` — Bulk update task records by IDs
- `delete_task_by_id` — Delete a task by ID (hard destroy)
- `delete_tasks` — Bulk delete tasks by IDs (hard destroy)

### ⚙️ Workflow (7 tools)
- `list_workflows` — List all workflow records
- `get_workflow_by_id` — Get a single workflow by ID
- `create_workflow` — Create a new workflow record
- `update_workflow` — Update an existing workflow record
- `update_workflows` — Bulk update workflow records by IDs
- `delete_workflow_by_id` — Delete a workflow by ID (hard destroy)
- `delete_workflows` — Bulk delete workflows by IDs (hard destroy)

### 👥 WorkspaceMember (7 tools)
- `list_workspace_members` — List all workspace member records
- `get_workspace_member_by_id` — Get a single workspace member by ID
- `create_workspace_member` — Create a new workspace member record
- `update_workspace_member` — Update an existing workspace member record
- `update_workspace_members` — Bulk update workspace member records by IDs
- `delete_workspace_member_by_id` — Delete a workspace member by ID (hard destroy)
- `delete_workspace_members` — Bulk delete workspace members by IDs (hard destroy)

### 📎 Attachment (7 tools)
- `list_attachments` — List all attachment records
- `get_attachment_by_id` — Get a single attachment by ID
- `create_attachment` — Create a new attachment record
- `update_attachment` — Update an existing attachment record
- `update_attachments` — Bulk update attachment records by IDs
- `delete_attachment_by_id` — Delete an attachment by ID (hard destroy)
- `delete_attachments` — Bulk delete attachments by IDs (hard destroy)

### 🎯 NoteTarget (7 tools)
- `list_note_targets` — List all note target records
- `get_note_target_by_id` — Get a single note target by ID
- `create_note_target` — Create a new note target record
- `update_note_target` — Update an existing note target record
- `update_note_targets` — Bulk update note target records by IDs
- `delete_note_target_by_id` — Delete a note target by ID (hard destroy)
- `delete_note_targets` — Bulk delete note targets by IDs (hard destroy)

### 🎯 TaskTarget (7 tools)
- `list_task_targets` — List all task target records
- `get_task_target_by_id` — Get a single task target by ID
- `create_task_target` — Create a new task target record
- `update_task_target` — Update an existing task target record
- `update_task_targets` — Bulk update task target records by IDs
- `delete_task_target_by_id` — Delete a task target by ID (hard destroy)
- `delete_task_targets` — Bulk delete task targets by IDs (hard destroy)

### 📅 TimelineActivity (7 tools)
- `list_timeline_activities` — List all timeline activity records
- `get_timeline_activity_by_id` — Get a single timeline activity by ID
- `create_timeline_activity` — Create a new timeline activity record
- `update_timeline_activity` — Update an existing timeline activity record
- `update_timeline_activities` — Bulk update timeline activity records by IDs
- `delete_timeline_activity_by_id` — Delete a timeline activity by ID (hard destroy)
- `delete_timeline_activities` — Bulk delete timeline activities by IDs (hard destroy)

### 🗓️ CalendarEvent (7 tools)
- `list_calendar_events` — List all calendar event records
- `get_calendar_event_by_id` — Get a single calendar event by ID
- `create_calendar_event` — Create a new calendar event record
- `update_calendar_event` — Update an existing calendar event record
- `update_calendar_events` — Bulk update calendar event records by IDs
- `delete_calendar_event_by_id` — Delete a calendar event by ID (hard destroy)
- `delete_calendar_events` — Bulk delete calendar events by IDs (hard destroy)

### 🗓️ CalendarEventParticipant (7 tools)
- `list_calendar_event_participants` — List all calendar event participant records
- `get_calendar_event_participant_by_id` — Get a single calendar event participant by ID
- `create_calendar_event_participant` — Create a new calendar event participant record
- `update_calendar_event_participant` — Update an existing calendar event participant record
- `update_calendar_event_participants` — Bulk update calendar event participant records by IDs
- `delete_calendar_event_participant_by_id` — Delete a calendar event participant by ID (hard destroy)
- `delete_calendar_event_participants` — Bulk delete calendar event participants by IDs (hard destroy)

### 💬 Message (7 tools)
- `list_messages` — List all message records
- `get_message_by_id` — Get a single message by ID
- `create_message` — Create a new message record
- `update_message` — Update an existing message record
- `update_messages` — Bulk update message records by IDs
- `delete_message_by_id` — Delete a message by ID (hard destroy)
- `delete_messages` — Bulk delete messages by IDs (hard destroy)

### 💬 MessageThread (7 tools)
- `list_message_threads` — List all message thread records
- `get_message_thread_by_id` — Get a single message thread by ID
- `create_message_thread` — Create a new message thread record
- `update_message_thread` — Update an existing message thread record
- `update_message_threads` — Bulk update message thread records by IDs
- `delete_message_thread_by_id` — Delete a message thread by ID (hard destroy)
- `delete_message_threads` — Bulk delete message threads by IDs (hard destroy)

### 💬 MessageParticipant (7 tools)
- `list_message_participants` — List all message participant records
- `get_message_participant_by_id` — Get a single message participant by ID
- `create_message_participant` — Create a new message participant record
- `update_message_participant` — Update an existing message participant record
- `update_message_participants` — Bulk update message participant records by IDs
- `delete_message_participant_by_id` — Delete a message participant by ID (hard destroy)
- `delete_message_participants` — Bulk delete message participants by IDs (hard destroy)

### 📞 CallRecording (7 tools)
- `list_call_recordings` — List all call recording records
- `get_call_recording_by_id` — Get a single call recording by ID
- `create_call_recording` — Create a new call recording record
- `update_call_recording` — Update an existing call recording record
- `update_call_recordings` — Bulk update call recording records by IDs
- `delete_call_recording_by_id` — Delete a call recording by ID (hard destroy)
- `delete_call_recordings` — Bulk delete call recordings by IDs (hard destroy)

### 🔧 Domain-Specific Tools (1 tool)
- `check_server_status` — Check connectivity to the Twenty backend API