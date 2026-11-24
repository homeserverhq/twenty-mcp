# Twenty MCP Audit Notes

## Repository

- **Repo:** `twenty-mcp`
- **Server:** FastMCP 3.4.2, streamable HTTP with SSE responses
- **Tools:** 115 across 17 resource domains plus `check_server_status`
- **Transport:** stateless HTTP by default (`IS_STATEFUL=false`)
- **Auth:** identity passthrough; the server forwards the caller's bearer token
- **Backend:** Twenty CRM v2.21.0 at `http://twenty-app:3000`
- **Storage:** PostgreSQL workspace `workspace_33rwona96s0uyjr293skptrnw`

## Execution environment

- Audit runs against a temporary container built from this repo:
  `twenty-mcp:audit` on `twenty_int-twenty-net`.
- Production `twenty-mcp` is not restarted by the audit.
- `ALLOW_ALL_AGGREGATE=false` is the production setting; the audit also
  verifies the `true` mode with a second container.
- The API key is **workspace-scoped** (`JWT sub == workspaceId`), not
  user-scoped. Cross-workspace isolation therefore cannot be tested against
  this single workspace.

## Decisions

1. **Pagination** — every list tool accepts `limit` (1–200) and
   `starting_after`, returning `items`, `total_count`, and `page_info`.
   The backend's default page size is 60, so the previous tools silently
   truncated larger collections.
2. **Aggregate projection is intentional.** `ALLOW_ALL_AGGREGATE=false`
   forces `include_all_fields=False` on `list_*`. This is a context-size
   guard, not a bug. The docstrings now state it, and the audit asserts the
   documented behavior in both flag states. Single-record `get_*` always
   honors the flag.
3. **Workspace-member bulk update** — the backend rejects the bulk
   `workspaceMembers` PATCH with `PERMISSION_DENIED`; the client now performs
   per-record PATCHes, and the audit changes and restores the admin member's
   `colorScheme`.
4. **Destructive safety** — the audit only deletes IDs it created. The
   legacy leak scan now matches only `t<current-run-id>-` artifacts; the old
   pattern matched every historical `t<hex>-` name and could delete older
   data.
5. **Rate limits** — Twenty allows 100 API calls per 60 seconds. Both the
   server client and the audit backend retry 429 responses using
   `Retry-After`.

## Baseline data

Snapshot before a full run:

| Resource | Records | Soft-deleted |
|---|---:|---:|
| company | 10 | 0 |
| person | 11 | 0 |
| opportunity | 12 | 0 |
| note | 19–20 | 0 |
| task | 19 | 0 |
| workflow | 2 | 0 |
| attachment | 0 | 0 |
| calendarEvent | 41–47 | 0 |
| message | 27 | 0 |
| timelineActivity | 298+ | 0 |

Counts drift slightly between runs because Twenty auto-creates timeline
activities for mutations and because earlier smoke runs may leave artifacts.
The audit compares before/after counts and treats `timelineActivity` growth as
a documented write side effect; the fixture-prefix scan is authoritative.

## Safety incident and correction

During the first legacy smoke run, `test_runner.py` still used its historical
leak heuristic: any `t<hex>-` name was treated as a current-run artifact. That
scan deleted six older calendar events left by previous test runs
(`t510981aa-Recurring`, `t85d8bae4-Meeting`, `tcacb584e-Meeting`,
`teefe52e0-Meeting`, `t85d8bae4-Event-upd`, `t510981aa-Event-upd`). They were
old test artifacts, not product data, but they were pre-existing relative to
this audit. The heuristic now matches only `t<current-run-id>-`, and the
488-test audit does not share that scan. Baseline calendar events moved from
47 to 41 as a result.

## Known limitations found by the audit

- **Message list** — `list_messages` returns `totalCount=27` with zero rows.
  The workspace has no `messageChannelMessageAssociation` rows. The same
  query returns zero edges through GraphQL while `GET /rest/messages/{id}`
  works. This is a backend association/visibility limitation; the MCP list
  tool now emits a `warning` when the backend reports more rows than it
  returns.
- **Calendar event list** — events created through the MCP have no
  `calendarChannelEventAssociation`, so `list_calendar_events` omits them
  while `get_calendar_event_by_id` returns them. The list tool warns on the
  count mismatch. Adding association support would require a calendar-channel
  parameter/tool, which is outside the current 115-tool surface.
- **Cross-workspace isolation** — only one workspace and one workspace-scoped
  API key are available; the suite tests invalid-token isolation and
  concurrent token handling, and records a justified skip for a second
  workspace.

## Commands

```bash
# Schema-only L0 needs no API key
docker exec twenty-mcp-audit python -m src.audit.runner --l0 --quiet

# Build the audit image
docker build -t twenty-mcp:audit .

# Start it beside Twenty
docker run -d --rm --name twenty-mcp-audit \
  --network twenty_int-twenty-net \
  -e TWENTY_BASE_URL=http://twenty-app:3000 \
  -e MCP_SERVER_PORT=80 \
  -e ALLOW_ALL_AGGREGATE=false \
  -e IS_STATEFUL=false \
  twenty-mcp:audit

# Run
docker exec -e API_KEY="$TWENTY_API_KEY" twenty-mcp-audit \
  python -m src.audit.runner --all --quiet \
  --report docs/tool-audit.md --json docs/tool-audit.json

# Legacy smoke suite
docker exec -e API_KEY="$TWENTY_API_KEY" twenty-mcp-audit \
  python -m src.test_runner
```
