import os
import datetime as dt
import re
import json
import urllib.parse
from typing import Any, Optional

import httpx


COMMON_FIELDS: dict[str, set[str]] = {
    "company":                    {"id", "name", "domainName"},
    "person":                     {"id", "name", "emails", "jobTitle", "companyId"},
    "opportunity":                {"id", "name", "amount", "stage", "companyId", "pointOfContactId"},
    "note":                       {"id", "title", "bodyV2", "createdAt"},
    "task":                       {"id", "title", "bodyV2", "status", "dueAt"},
    "workflow":                   {"id", "name", "statuses", "lastPublishedVersionId"},
    "workspaceMember":            {"id", "name", "userEmail", "colorScheme"},
    "attachment":                 {"id", "name", "fullPath", "type", "createdAt"},
    "noteTarget":                 {"id", "noteId", "targetPersonId", "targetCompanyId", "targetOpportunityId"},
    "taskTarget":                 {"id", "taskId", "targetPersonId", "targetCompanyId", "targetOpportunityId"},
    "timelineActivity":           {"id", "name", "happensAt", "workspaceMemberId", "linkedRecordCachedName"},
    "calendarEvent":              {"id", "title", "startsAt", "endsAt"},
    "calendarEventParticipant":   {"id", "calendarEventId", "handle", "displayName", "responseStatus"},
    "message":                    {"id", "subject", "text", "messageThreadId", "receivedAt"},
    "messageThread":              {"id", "subject", "createdAt"},
    "messageParticipant":         {"id", "messageId", "handle", "displayName", "role"},
    "callRecording":              {"id", "title", "status", "startedAt", "calendarEventId"},
}


def _filter_fields(data: Any, common_set: set[str]) -> Any:
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in common_set}
    if isinstance(data, list):
        return [_filter_fields(item, common_set) for item in data]
    return data


def _normalize_datetime(value: str) -> str:
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', value):
        parsed = dt.datetime.fromisoformat(value)
        parsed = parsed.astimezone(dt.timezone.utc)
        return parsed.strftime('%Y-%m-%d %H:%M:%S')
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
        raise ValueError(
            f"Invalid datetime: {value}. Timezone offset is required. "
            "Must use format: 2026-06-22T15:00:00-04:00"
        )
    return value


class TwentyClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("Twenty_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            raise ValueError(
                "Twenty BASE_URL required. Set Twenty_BASE_URL env var "
                "or pass base_url."
            )

    def _get_headers(self, api_key: Optional[str] = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for k, v in payload.items():
            if isinstance(v, str):
                result[k] = _normalize_datetime(v) if re.match(
                    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', v
                ) else v
            else:
                result[k] = v
        return result

    async def request(
        self,
        method: str,
        path: str,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._get_headers(api_key)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            if response.status_code >= 400:
                body = ""
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        body = response.json()
                    else:
                        body = response.text
                except Exception:
                    body = response.text[:500]
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code} for {method} {path}: {body}",
                    request=response.request,
                    response=response,
                )
            if response.status_code == 204:
                return {}
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return {"text": response.text}

    async def get(self, path: str, api_key: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.request("GET", path, api_key, **kwargs)

    async def post(self, path: str, api_key: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.request("POST", path, api_key, **kwargs)

    async def patch(self, path: str, api_key: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.request("PATCH", path, api_key, **kwargs)

    async def delete(self, path: str, api_key: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.request("DELETE", path, api_key, **kwargs)

    # =========================================================================
    # Company
    # =========================================================================
    async def get_all_companies(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/companies", api_key)
        data = raw.get("data", {}).get("companies", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["company"])
        return data

    async def get_company_by_id(self, company_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/companies/{company_id}", api_key)
        data = raw.get("data", {}).get("company", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["company"])
        return data

    async def create_company(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/companies", api_key, json=normalized)
        data = raw.get("data", {}).get("createCompany", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["company"])
        return data

    async def update_company(self, company_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/companies/{company_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCompany", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["company"])
        return data

    async def update_companies(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/companies?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCompanies", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["company"])
        return data

    async def delete_company_by_id(self, company_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/companies/{company_id}", api_key)

    async def delete_companies(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/companies?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Person
    # =========================================================================
    async def get_all_people(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/people", api_key)
        data = raw.get("data", {}).get("people", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["person"])
        return data

    async def get_person_by_id(self, person_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/people/{person_id}", api_key)
        data = raw.get("data", {}).get("person", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["person"])
        return data

    async def create_person(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/people", api_key, json=normalized)
        data = raw.get("data", {}).get("createPerson", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["person"])
        return data

    async def update_person(self, person_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/people/{person_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updatePerson", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["person"])
        return data

    async def update_people(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/people?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updatePeople", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["person"])
        return data

    async def delete_person_by_id(self, person_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/people/{person_id}", api_key)

    async def delete_people(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/people?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Opportunity
    # =========================================================================
    async def get_all_opportunities(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/opportunities", api_key)
        data = raw.get("data", {}).get("opportunities", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["opportunity"])
        return data

    async def get_opportunity_by_id(self, opportunity_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/opportunities/{opportunity_id}", api_key)
        data = raw.get("data", {}).get("opportunity", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["opportunity"])
        return data

    async def create_opportunity(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/opportunities", api_key, json=normalized)
        data = raw.get("data", {}).get("createOpportunity", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["opportunity"])
        return data

    async def update_opportunity(self, opportunity_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/opportunities/{opportunity_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateOpportunity", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["opportunity"])
        return data

    async def update_opportunities(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/opportunities?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateOpportunities", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["opportunity"])
        return data

    async def delete_opportunity_by_id(self, opportunity_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/opportunities/{opportunity_id}", api_key)

    async def delete_opportunities(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/opportunities?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Note
    # =========================================================================
    async def get_all_notes(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/notes", api_key)
        data = raw.get("data", {}).get("notes", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["note"])
        return data

    async def get_note_by_id(self, note_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/notes/{note_id}", api_key)
        data = raw.get("data", {}).get("note", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["note"])
        return data

    async def create_note(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/notes", api_key, json=normalized)
        data = raw.get("data", {}).get("createNote", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["note"])
        return data

    async def update_note(self, note_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/notes/{note_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateNote", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["note"])
        return data

    async def update_notes(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/notes?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateNotes", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["note"])
        return data

    async def delete_note_by_id(self, note_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/notes/{note_id}", api_key)

    async def delete_notes(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/notes?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Task
    # =========================================================================
    async def get_all_tasks(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/tasks", api_key)
        data = raw.get("data", {}).get("tasks", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["task"])
        return data

    async def get_task_by_id(self, task_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/tasks/{task_id}", api_key)
        data = raw.get("data", {}).get("task", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["task"])
        return data

    async def create_task(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/tasks", api_key, json=normalized)
        data = raw.get("data", {}).get("createTask", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["task"])
        return data

    async def update_task(self, task_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/tasks/{task_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateTask", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["task"])
        return data

    async def update_tasks(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/tasks?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateTasks", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["task"])
        return data

    async def delete_task_by_id(self, task_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/tasks/{task_id}", api_key)

    async def delete_tasks(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/tasks?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Workflow
    # =========================================================================
    async def get_all_workflows(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/workflows", api_key)
        data = raw.get("data", {}).get("workflows", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workflow"])
        return data

    async def get_workflow_by_id(self, workflow_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/workflows/{workflow_id}", api_key)
        data = raw.get("data", {}).get("workflow", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workflow"])
        return data

    async def create_workflow(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/workflows", api_key, json=normalized)
        data = raw.get("data", {}).get("createWorkflow", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workflow"])
        return data

    async def update_workflow(self, workflow_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/workflows/{workflow_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateWorkflow", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workflow"])
        return data

    async def delete_workflow_by_id(self, workflow_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/workflows/{workflow_id}", api_key)

    # =========================================================================
    # WorkspaceMember
    # =========================================================================
    async def get_all_workspace_members(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/workspaceMembers", api_key)
        data = raw.get("data", {}).get("workspaceMembers", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workspaceMember"])
        return data

    async def get_workspace_member_by_id(self, workspace_member_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/workspaceMembers/{workspace_member_id}", api_key)
        data = raw.get("data", {}).get("workspaceMember", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workspaceMember"])
        return data

    async def update_workspace_member(self, workspace_member_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/workspaceMembers/{workspace_member_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateWorkspaceMember", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workspaceMember"])
        return data

    async def update_workspace_members(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/workspaceMembers?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateWorkspaceMembers", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["workspaceMember"])
        return data

    async def delete_workspace_member_by_id(self, workspace_member_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/workspaceMembers/{workspace_member_id}", api_key)

    async def delete_workspace_members(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/workspaceMembers?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Attachment
    # =========================================================================
    async def get_all_attachments(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/attachments", api_key)
        data = raw.get("data", {}).get("attachments", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["attachment"])
        return data

    async def get_attachment_by_id(self, attachment_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/attachments/{attachment_id}", api_key)
        data = raw.get("data", {}).get("attachment", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["attachment"])
        return data

    async def create_attachment(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/attachments", api_key, json=normalized)
        data = raw.get("data", {}).get("createAttachment", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["attachment"])
        return data

    async def update_attachment(self, attachment_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/attachments/{attachment_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateAttachment", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["attachment"])
        return data

    async def update_attachments(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/attachments?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateAttachments", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["attachment"])
        return data

    async def delete_attachment_by_id(self, attachment_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/attachments/{attachment_id}", api_key)

    async def delete_attachments(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/attachments?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # NoteTarget
    # =========================================================================
    async def get_all_note_targets(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/noteTargets", api_key)
        data = raw.get("data", {}).get("noteTargets", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["noteTarget"])
        return data

    async def get_note_target_by_id(self, note_target_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/noteTargets/{note_target_id}", api_key)
        data = raw.get("data", {}).get("noteTarget", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["noteTarget"])
        return data

    async def create_note_target(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/noteTargets", api_key, json=normalized)
        data = raw.get("data", {}).get("createNoteTarget", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["noteTarget"])
        return data

    async def update_note_target(self, note_target_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/noteTargets/{note_target_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateNoteTarget", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["noteTarget"])
        return data

    async def update_note_targets(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/noteTargets?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateNoteTargets", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["noteTarget"])
        return data

    async def delete_note_target_by_id(self, note_target_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/noteTargets/{note_target_id}", api_key)

    async def delete_note_targets(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/noteTargets?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # TaskTarget
    # =========================================================================
    async def get_all_task_targets(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/taskTargets", api_key)
        data = raw.get("data", {}).get("taskTargets", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["taskTarget"])
        return data

    async def get_task_target_by_id(self, task_target_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/taskTargets/{task_target_id}", api_key)
        data = raw.get("data", {}).get("taskTarget", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["taskTarget"])
        return data

    async def create_task_target(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/taskTargets", api_key, json=normalized)
        data = raw.get("data", {}).get("createTaskTarget", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["taskTarget"])
        return data

    async def update_task_target(self, task_target_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/taskTargets/{task_target_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateTaskTarget", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["taskTarget"])
        return data

    async def update_task_targets(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/taskTargets?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateTaskTargets", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["taskTarget"])
        return data

    async def delete_task_target_by_id(self, task_target_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/taskTargets/{task_target_id}", api_key)

    async def delete_task_targets(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/taskTargets?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # TimelineActivity
    # =========================================================================
    async def get_all_timeline_activities(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/timelineActivities", api_key)
        data = raw.get("data", {}).get("timelineActivities", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["timelineActivity"])
        return data

    async def get_timeline_activity_by_id(self, timeline_activity_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/timelineActivities/{timeline_activity_id}", api_key)
        data = raw.get("data", {}).get("timelineActivity", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["timelineActivity"])
        return data

    async def create_timeline_activity(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/timelineActivities", api_key, json=normalized)
        data = raw.get("data", {}).get("createTimelineActivity", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["timelineActivity"])
        return data

    async def update_timeline_activity(self, timeline_activity_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/timelineActivities/{timeline_activity_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateTimelineActivity", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["timelineActivity"])
        return data

    async def update_timeline_activities(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/timelineActivities?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateTimelineActivities", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["timelineActivity"])
        return data

    async def delete_timeline_activity_by_id(self, timeline_activity_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/timelineActivities/{timeline_activity_id}", api_key)

    async def delete_timeline_activities(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/timelineActivities?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # CalendarEvent
    # =========================================================================
    async def get_all_calendar_events(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/calendarEvents", api_key)
        data = raw.get("data", {}).get("calendarEvents", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEvent"])
        return data

    async def get_calendar_event_by_id(self, calendar_event_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/calendarEvents/{calendar_event_id}", api_key)
        data = raw.get("data", {}).get("calendarEvent", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEvent"])
        return data

    async def create_calendar_event(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/calendarEvents", api_key, json=normalized)
        data = raw.get("data", {}).get("createCalendarEvent", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEvent"])
        return data

    async def update_calendar_event(self, calendar_event_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/calendarEvents/{calendar_event_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCalendarEvent", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEvent"])
        return data

    async def update_calendar_events(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/calendarEvents?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCalendarEvents", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEvent"])
        return data

    async def delete_calendar_event_by_id(self, calendar_event_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/calendarEvents/{calendar_event_id}", api_key)

    async def delete_calendar_events(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/calendarEvents?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # CalendarEventParticipant
    # =========================================================================
    async def get_all_calendar_event_participants(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/calendarEventParticipants", api_key)
        data = raw.get("data", {}).get("calendarEventParticipants", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEventParticipant"])
        return data

    async def get_calendar_event_participant_by_id(self, calendar_event_participant_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/calendarEventParticipants/{calendar_event_participant_id}", api_key)
        data = raw.get("data", {}).get("calendarEventParticipant", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEventParticipant"])
        return data

    async def create_calendar_event_participant(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/calendarEventParticipants", api_key, json=normalized)
        data = raw.get("data", {}).get("createCalendarEventParticipant", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEventParticipant"])
        return data

    async def update_calendar_event_participant(self, calendar_event_participant_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/calendarEventParticipants/{calendar_event_participant_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCalendarEventParticipant", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEventParticipant"])
        return data

    async def update_calendar_event_participants(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/calendarEventParticipants?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCalendarEventParticipants", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["calendarEventParticipant"])
        return data

    async def delete_calendar_event_participant_by_id(self, calendar_event_participant_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/calendarEventParticipants/{calendar_event_participant_id}", api_key)

    async def delete_calendar_event_participants(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/calendarEventParticipants?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # Message
    # =========================================================================
    async def get_all_messages(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/messages", api_key)
        data = raw.get("data", {}).get("messages", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["message"])
        return data

    async def get_message_by_id(self, message_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/messages/{message_id}", api_key)
        data = raw.get("data", {}).get("message", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["message"])
        return data

    async def create_message(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/messages", api_key, json=normalized)
        data = raw.get("data", {}).get("createMessage", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["message"])
        return data

    async def update_message(self, message_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/messages/{message_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateMessage", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["message"])
        return data

    async def update_messages(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/messages?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateMessages", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["message"])
        return data

    async def delete_message_by_id(self, message_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/messages/{message_id}", api_key)

    async def delete_messages(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/messages?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # MessageThread
    # =========================================================================
    async def get_all_message_threads(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/messageThreads", api_key)
        data = raw.get("data", {}).get("messageThreads", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageThread"])
        return data

    async def get_message_thread_by_id(self, message_thread_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/messageThreads/{message_thread_id}", api_key)
        data = raw.get("data", {}).get("messageThread", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageThread"])
        return data

    async def create_message_thread(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/messageThreads", api_key, json=normalized)
        data = raw.get("data", {}).get("createMessageThread", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageThread"])
        return data

    async def update_message_thread(self, message_thread_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/messageThreads/{message_thread_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateMessageThread", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageThread"])
        return data

    async def update_message_threads(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/messageThreads?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateMessageThreads", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageThread"])
        return data

    async def delete_message_thread_by_id(self, message_thread_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/messageThreads/{message_thread_id}", api_key)

    async def delete_message_threads(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/messageThreads?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # MessageParticipant
    # =========================================================================
    async def get_all_message_participants(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/messageParticipants", api_key)
        data = raw.get("data", {}).get("messageParticipants", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageParticipant"])
        return data

    async def get_message_participant_by_id(self, message_participant_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/messageParticipants/{message_participant_id}", api_key)
        data = raw.get("data", {}).get("messageParticipant", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageParticipant"])
        return data

    async def create_message_participant(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/messageParticipants", api_key, json=normalized)
        data = raw.get("data", {}).get("createMessageParticipant", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageParticipant"])
        return data

    async def update_message_participant(self, message_participant_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/messageParticipants/{message_participant_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateMessageParticipant", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageParticipant"])
        return data

    async def update_message_participants(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/messageParticipants?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateMessageParticipants", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["messageParticipant"])
        return data

    async def delete_message_participant_by_id(self, message_participant_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/messageParticipants/{message_participant_id}", api_key)

    async def delete_message_participants(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/messageParticipants?filter=id[in]:{id_list}", api_key)

    # =========================================================================
    # CallRecording
    # =========================================================================
    async def get_all_call_recordings(self, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get("/rest/callRecordings", api_key)
        data = raw.get("data", {}).get("callRecordings", [])
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["callRecording"])
        return data

    async def get_call_recording_by_id(self, call_recording_id: str, api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        raw = await self.get(f"/rest/callRecordings/{call_recording_id}", api_key)
        data = raw.get("data", {}).get("callRecording", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["callRecording"])
        return data

    async def create_call_recording(self, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.post("/rest/callRecordings", api_key, json=normalized)
        data = raw.get("data", {}).get("createCallRecording", {})
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["callRecording"])
        return data

    async def update_call_recording(self, call_recording_id: str, payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/callRecordings/{call_recording_id}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCallRecording", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["callRecording"])
        return data

    async def update_call_recordings(self, ids: list[str], payload: dict[str, Any], api_key: Optional[str] = None, include_all_fields: bool = False) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        normalized = self._normalize_payload(payload)
        raw = await self.patch(f"/rest/callRecordings?filter=id[in]:{id_list}", api_key, json=normalized)
        data = raw.get("data", {}).get("updateCallRecordings", {})
        if isinstance(data, list): return {"updated": data}
        if not include_all_fields:
            data = _filter_fields(data, COMMON_FIELDS["callRecording"])
        return data

    async def delete_call_recording_by_id(self, call_recording_id: str, api_key: Optional[str] = None) -> Any:
        return await self.delete(f"/rest/callRecordings/{call_recording_id}", api_key)

    async def delete_call_recordings(self, ids: list[str], api_key: Optional[str] = None) -> Any:
        id_list = '[' + ','.join(str(i) for i in ids) + ']'
        return await self.delete(f"/rest/callRecordings?filter=id[in]:{id_list}", api_key)