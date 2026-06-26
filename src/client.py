import os
import datetime as dt
import re
from typing import Any, Optional

import httpx


COMMON_FIELDS: dict[str, set[str]] = {
    "company": {"id", "name", "domainName", "companyType", "industry"},
    "person": {"id", "name", "emails", "jobTitle", "companyId"},
    "opportunity": {"id", "name", "amount", "stage", "companyId"},
    "task": {"id", "title", "bodyV2", "status", "dueAt"},
    "note": {"id", "title", "bodyV2", "createdAt"},
    "attachment": {"id", "name", "fullPath", "type", "createdAt"},
    "favorite": {"id", "viewId", "companyId", "personId"},
    "workflow": {"id", "name", "status", "lastPublishedVersionId"},
    "workflowVersion": {"id", "workflowId", "name", "status", "version"},
    "workflowRun": {"id", "workflowId", "status", "workflowVersionId"},
    "workflowAutomatedTrigger": {"id", "workflowId", "type", "settings"},
    "calendarEvent": {"id", "title", "startsAt", "endsAt", "calendarChannelId"},
    "calendarChannel": {"id", "handle", "type", "visibility", "syncStatus"},
    "calendarChannelEventAssociation": {"id", "calendarChannelId", "calendarEventId", "eventExternalId"},
    "calendarEventParticipant": {"id", "calendarEventId", "handle", "displayName", "responseStatus"},
    "message": {"id", "subject", "text", "messageThreadId", "receivedAt"},
    "messageThread": {"id", "subject", "createdAt", "updatedAt"},
    "messageChannel": {"id", "handle", "type", "visibility"},
    "messageParticipant": {"id", "messageId", "handle", "displayName", "role"},
    "messageFolder": {"id", "name", "messageChannelId", "isSynced", "isSentFolder"},
    "messageChannelMessageAssociation": {"id", "messageChannelId", "messageId", "direction"},
    "noteTarget": {"id", "noteId", "personId", "companyId", "opportunityId"},
    "taskTarget": {"id", "taskId", "personId", "companyId", "opportunityId"},
    "timelineActivity": {"id", "name", "happensAt", "workspaceMemberId", "linkedRecordCachedName"},
    "workspaceMember": {"id", "name", "userEmail", "role", "colorScheme"},
    "connectedAccount": {"id", "handle", "provider", "visibility"},
    "favoriteFolder": {"id", "name", "createdAt"},
    "dashboard": {"id", "title", "position", "pageLayoutId"},
    "blocklist": {"id", "handle", "workspaceMemberId", "createdAt"},
}

ALLOW_ALL_AGGREGATE = os.getenv("ALLOW_ALL_AGGREGATE", "false").lower() in ("true", "1", "yes")


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
        self.base_url = base_url or os.getenv("TWENTY_BASE_URL", "http://twenty-app:3000")
        self.rest_path = "/rest/"

    def _get_headers(self, token: Optional[str]) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        token: Optional[str],
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{self.rest_path}{path}"
        headers = self._get_headers(token)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method, url=url, headers=headers, params=params, json=json
            )
        if response.status_code == 204:
            return {}
        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")
        return response.json()

    async def get(
        self, path: str, token: Optional[str], params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        return await self._request("GET", path, token, params=params)

    async def post(
        self, path: str, token: Optional[str], json: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        return await self._request("POST", path, token, json=json)

    async def patch(
        self,
        path: str,
        token: Optional[str],
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", path, token, params=params, json=json)

    async def delete(
        self, path: str, token: Optional[str], params: Optional[dict[str, Any]] = None, json: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        return await self._request("DELETE", path, token, params=params, json=json)

    def _extract_list(self, data: dict[str, Any], plural: str) -> list[dict[str, Any]]:
        if plural in data.get("data", {}):
            return data["data"][plural]
        return []

    def _extract_single(self, data: dict[str, Any], singular: str) -> dict[str, Any]:
        if singular in data.get("data", {}):
            return data["data"][singular]
        return {}

    # =============================================================================
    # companies
    # =============================================================================

    async def get_all_companies(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("companies", token)
        items = self._extract_list(data, "companies")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["company"])
        return items

    async def get_company_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"companies/{id}", token)
        item = self._extract_single(data, "company")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["company"])
        return item

    async def create_company(
        self,
        token: Optional[str],
        name: str,
        domainName: Optional[dict[str, Any]] = None,
        companyType: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
        employees: Optional[int] = None,
        linkedinUrl: Optional[str] = None,
        annualRecurringRevenue: Optional[dict[str, Any]] = None,
        address: Optional[dict[str, Any]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {"name": name}
        if domainName is not None:
            attrs["domainName"] = domainName
        if companyType:
            attrs["companyType"] = companyType
        if industry:
            attrs["industry"] = industry
        if description:
            attrs["description"] = description
        if employees is not None:
            attrs["employees"] = employees
        if linkedinUrl:
            attrs["linkedinUrl"] = linkedinUrl
        if annualRecurringRevenue is not None:
            attrs["annualRecurringRevenue"] = annualRecurringRevenue
        if address is not None:
            attrs["address"] = address
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = _normalize_datetime(v)
        data = await self.post("companies", token, json=attrs)
        item = self._extract_single(data, "createCompany")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["company"])
        return item

    async def update_company(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        domainName: Optional[dict[str, Any]] = None,
        companyType: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
        employees: Optional[int] = None,
        linkedinUrl: Optional[str] = None,
        annualRecurringRevenue: Optional[dict[str, Any]] = None,
        address: Optional[dict[str, Any]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {}
        if name is not None:
            attrs["name"] = name
        if domainName is not None:
            attrs["domainName"] = domainName
        if companyType is not None:
            attrs["companyType"] = companyType
        if industry is not None:
            attrs["industry"] = industry
        if description is not None:
            attrs["description"] = description
        if employees is not None:
            attrs["employees"] = employees
        if linkedinUrl is not None:
            attrs["linkedinUrl"] = linkedinUrl
        if annualRecurringRevenue is not None:
            attrs["annualRecurringRevenue"] = annualRecurringRevenue
        if address is not None:
            attrs["address"] = address
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = _normalize_datetime(v)
        data = await self.patch(f"companies/{id}", token, json=attrs)
        item = self._extract_single(data, "updateCompany")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["company"])
        return item

    async def update_many_companies(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        name: Optional[str] = None,
        companyType: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
        employees: Optional[int] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if name is not None:
            attrs["name"] = name
        if companyType is not None:
            attrs["companyType"] = companyType
        if industry is not None:
            attrs["industry"] = industry
        if description is not None:
            attrs["description"] = description
        if employees is not None:
            attrs["employees"] = employees
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = _normalize_datetime(v)
        data = await self.patch("companies", token, params=params, json=attrs)
        items = data.get("data", {}).get("updateCompanies", [])
        return items

    async def delete_company_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"companies/{id}", token)

    async def delete_many_companies(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("companies", token, params=params)
        return data.get("data", {}).get("deleteCompanies", [])

    # =============================================================================
    # people
    # =============================================================================

    async def get_all_people(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("people", token)
        items = self._extract_list(data, "people")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["person"])
        return items

    async def get_person_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"people/{id}", token)
        item = self._extract_single(data, "person")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["person"])
        return item

    async def create_person(
        self,
        token: Optional[str],
        name: dict[str, Any],
        emails: dict[str, Any],
        firstName: Optional[str] = None,
        lastName: Optional[str] = None,
        jobTitle: Optional[str] = None,
        linkedinUrl: Optional[str] = None,
        phones: Optional[dict[str, Any]] = None,
        city: Optional[str] = None,
        companyId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name:
            attrs["name"] = name
        if emails:
            attrs["emails"] = emails
        if firstName:
            attrs["firstName"] = firstName
        if lastName:
            attrs["lastName"] = lastName
        if jobTitle:
            attrs["jobTitle"] = jobTitle
        if linkedinUrl:
            attrs["linkedinUrl"] = linkedinUrl
        if phones is not None:
            attrs["phones"] = phones
        if city:
            attrs["city"] = city
        if companyId:
            attrs["companyId"] = companyId
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = _normalize_datetime(v)
        data = await self.post("people", token, json=attrs)
        item = self._extract_single(data, "createPerson")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["person"])
        return item

    async def update_person(
        self,
        id: str,
        token: Optional[str],
        name: Optional[dict[str, Any]] = None,
        emails: Optional[dict[str, Any]] = None,
        jobTitle: Optional[str] = None,
        phones: Optional[dict[str, Any]] = None,
        city: Optional[str] = None,
        companyId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if emails is not None:
            attrs["emails"] = emails
        if jobTitle is not None:
            attrs["jobTitle"] = jobTitle
        if phones is not None:
            attrs["phones"] = phones
        if city is not None:
            attrs["city"] = city
        if companyId is not None:
            attrs["companyId"] = companyId
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = _normalize_datetime(v)
        data = await self.patch(f"people/{id}", token, json=attrs)
        item = self._extract_single(data, "updatePerson")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["person"])
        return item

    async def update_many_people(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        jobTitle: Optional[str] = None,
        city: Optional[str] = None,
        companyId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if jobTitle is not None:
            attrs["jobTitle"] = jobTitle
        if city is not None:
            attrs["city"] = city
        if companyId is not None:
            attrs["companyId"] = companyId
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = _normalize_datetime(v)
        data = await self.patch("people", token, params=params, json=attrs)
        return data.get("data", {}).get("updatePeople", [])

    async def delete_person_by_id(self, id: str, token: Optional[str]) -> dict[str, Any]:
        return await self.delete(f"people/{id}", token)

    async def delete_many_people(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("people", token, params=params)
        return data.get("data", {}).get("deletePeople", [])

    # =============================================================================
    # opportunities
    # =============================================================================

    async def get_all_opportunities(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("opportunities", token)
        items = self._extract_list(data, "opportunities")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["opportunity"])
        return items

    async def get_opportunity_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"opportunities/{id}", token)
        item = self._extract_single(data, "opportunity")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["opportunity"])
        return item

    async def create_opportunity(
        self,
        token: Optional[str],
        name: str,
        stage: str,
        amount: Optional[dict[str, Any]] = None,
        probability: Optional[int] = None,
        closeDate: Optional[str] = None,
        companyId: Optional[str] = None,
        personId: Optional[str] = None,
        description: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {"name": name, "stage": stage}
        if amount is not None:
            attrs["amount"] = amount
        if probability is not None:
            attrs["probability"] = probability
        if closeDate is not None:
            attrs["closeDate"] = _normalize_datetime(closeDate)
        if companyId:
            attrs["companyId"] = companyId
        if personId:
            attrs["personId"] = personId
        if description:
            attrs["description"] = description
        data = await self.post("opportunities", token, json=attrs)
        item = self._extract_single(data, "createOpportunity")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["opportunity"])
        return item

    async def update_opportunity(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        stage: Optional[str] = None,
        amount: Optional[dict[str, Any]] = None,
        probability: Optional[int] = None,
        closeDate: Optional[str] = None,
        companyId: Optional[str] = None,
        personId: Optional[str] = None,
        description: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if stage is not None:
            attrs["stage"] = stage
        if amount is not None:
            attrs["amount"] = amount
        if probability is not None:
            attrs["probability"] = probability
        if closeDate is not None:
            attrs["closeDate"] = _normalize_datetime(closeDate)
        if companyId is not None:
            attrs["companyId"] = companyId
        if personId is not None:
            attrs["personId"] = personId
        if description is not None:
            attrs["description"] = description
        data = await self.patch(f"opportunities/{id}", token, json=attrs)
        item = self._extract_single(data, "updateOpportunity")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["opportunity"])
        return item

    async def update_many_opportunities(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        stage: Optional[str] = None,
        probability: Optional[int] = None,
        companyId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if stage is not None:
            attrs["stage"] = stage
        if probability is not None:
            attrs["probability"] = probability
        if companyId is not None:
            attrs["companyId"] = companyId
        data = await self.patch("opportunities", token, params=params, json=attrs)
        return data.get("data", {}).get("updateOpportunities", [])

    async def delete_opportunity_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"opportunities/{id}", token)

    async def delete_many_opportunities(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("opportunities", token, params=params)
        return data.get("data", {}).get("deleteOpportunities", [])

    # =============================================================================
    # tasks
    # =============================================================================

    async def get_all_tasks(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("tasks", token)
        items = self._extract_list(data, "tasks")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["task"])
        return items

    async def get_task_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"tasks/{id}", token)
        item = self._extract_single(data, "task")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["task"])
        return item

    async def create_task(
        self,
        token: Optional[str],
        title: str,
        status: str,
        dueAt: Optional[str] = None,
        bodyV2: Optional[dict[str, Any]] = None,
        assigneeId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {"title": title, "status": status}
        if dueAt is not None:
            attrs["dueAt"] = _normalize_datetime(dueAt)
        if bodyV2 is not None:
            attrs["bodyV2"] = bodyV2
        if assigneeId:
            attrs["assigneeId"] = assigneeId
        data = await self.post("tasks", token, json=attrs)
        item = self._extract_single(data, "createTask")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["task"])
        return item

    async def update_task(
        self,
        id: str,
        token: Optional[str],
        title: Optional[str] = None,
        status: Optional[str] = None,
        dueAt: Optional[str] = None,
        bodyV2: Optional[dict[str, Any]] = None,
        assigneeId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if title is not None:
            attrs["title"] = title
        if status is not None:
            attrs["status"] = status
        if dueAt is not None:
            attrs["dueAt"] = _normalize_datetime(dueAt)
        if bodyV2 is not None:
            attrs["bodyV2"] = bodyV2
        if assigneeId is not None:
            attrs["assigneeId"] = assigneeId
        data = await self.patch(f"tasks/{id}", token, json=attrs)
        item = self._extract_single(data, "updateTask")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["task"])
        return item

    async def update_many_tasks(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        status: Optional[str] = None,
        assigneeId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if status is not None:
            attrs["status"] = status
        if assigneeId is not None:
            attrs["assigneeId"] = assigneeId
        data = await self.patch("tasks", token, params=params, json=attrs)
        return data.get("data", {}).get("updateTasks", [])

    async def delete_task_by_id(self, id: str, token: Optional[str]) -> dict[str, Any]:
        return await self.delete(f"tasks/{id}", token)

    async def delete_many_tasks(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("tasks", token, params=params)
        return data.get("data", {}).get("deleteTasks", [])

    # =============================================================================
    # notes
    # =============================================================================

    async def get_all_notes(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("notes", token)
        items = self._extract_list(data, "notes")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["note"])
        return items

    async def get_note_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"notes/{id}", token)
        item = self._extract_single(data, "note")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["note"])
        return item

    async def create_note(
        self,
        token: Optional[str],
        title: str,
        bodyV2: Optional[dict[str, Any]] = None,
        authorId: Optional[str] = None,
        pinned: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {"title": title}
        if bodyV2 is not None:
            attrs["bodyV2"] = bodyV2
        if authorId:
            attrs["authorId"] = authorId
        if pinned is not None:
            attrs["pinned"] = pinned
        data = await self.post("notes", token, json=attrs)
        item = self._extract_single(data, "createNote")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["note"])
        return item

    async def update_note(
        self,
        id: str,
        token: Optional[str],
        title: Optional[str] = None,
        bodyV2: Optional[dict[str, Any]] = None,
        pinned: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if title is not None:
            attrs["title"] = title
        if bodyV2 is not None:
            attrs["bodyV2"] = bodyV2
        if pinned is not None:
            attrs["pinned"] = pinned
        data = await self.patch(f"notes/{id}", token, json=attrs)
        item = self._extract_single(data, "updateNote")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["note"])
        return item

    async def update_many_notes(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        pinned: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if pinned is not None:
            attrs["pinned"] = pinned
        data = await self.patch("notes", token, params=params, json=attrs)
        return data.get("data", {}).get("updateNotes", [])

    async def delete_note_by_id(self, id: str, token: Optional[str]) -> dict[str, Any]:
        return await self.delete(f"notes/{id}", token)

    async def delete_many_notes(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("notes", token, params=params)
        return data.get("data", {}).get("deleteNotes", [])

    # =============================================================================
    # attachments
    # =============================================================================

    async def get_all_attachments(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("attachments", token)
        items = self._extract_list(data, "attachments")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["attachment"])
        return items

    async def get_attachment_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"attachments/{id}", token)
        item = self._extract_single(data, "attachment")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["attachment"])
        return item

    async def create_attachment(
        self,
        token: Optional[str],
        name: str,
        fullPath: str,
        type: Optional[str] = None,
        fileCategory: Optional[str] = None,
        authorId: Optional[str] = None,
        taskId: Optional[str] = None,
        noteId: Optional[str] = None,
        personId: Optional[str] = None,
        companyId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {"name": name, "fullPath": fullPath}
        if type:
            attrs["type"] = type
        if fileCategory:
            attrs["fileCategory"] = fileCategory
        if authorId:
            attrs["authorId"] = authorId
        if taskId:
            attrs["taskId"] = taskId
        if noteId:
            attrs["noteId"] = noteId
        if personId:
            attrs["personId"] = personId
        if companyId:
            attrs["companyId"] = companyId
        if opportunityId:
            attrs["opportunityId"] = opportunityId
        data = await self.post("attachments", token, json=attrs)
        item = self._extract_single(data, "createAttachment")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["attachment"])
        return item

    async def update_attachment(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        fullPath: Optional[str] = None,
        type: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if fullPath is not None:
            attrs["fullPath"] = fullPath
        if type is not None:
            attrs["type"] = type
        data = await self.patch(f"attachments/{id}", token, json=attrs)
        item = self._extract_single(data, "updateAttachment")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["attachment"])
        return item

    async def update_many_attachments(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        name: Optional[str] = None,
        type: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if name is not None:
            attrs["name"] = name
        if type is not None:
            attrs["type"] = type
        data = await self.patch("attachments", token, params=params, json=attrs)
        return data.get("data", {}).get("updateAttachments", [])

    async def delete_attachment_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"attachments/{id}", token)

    async def delete_many_attachments(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("attachments", token, params=params)
        return data.get("data", {}).get("deleteAttachments", [])

    # =============================================================================
    # favorites
    # =============================================================================

    async def get_all_favorites(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("favorites", token)
        items = self._extract_list(data, "favorites")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["favorite"])
        return items

    async def get_favorite_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"favorites/{id}", token)
        item = self._extract_single(data, "favorite")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["favorite"])
        return item

    async def create_favorite(
        self,
        token: Optional[str],
        viewId: str,
        companyId: Optional[str] = None,
        personId: Optional[str] = None,
        taskId: Optional[str] = None,
        noteId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs = {"viewId": viewId}
        if companyId:
            attrs["companyId"] = companyId
        if personId:
            attrs["personId"] = personId
        if taskId:
            attrs["taskId"] = taskId
        if noteId:
            attrs["noteId"] = noteId
        if opportunityId:
            attrs["opportunityId"] = opportunityId
        data = await self.post("favorites", token, json=attrs)
        item = self._extract_single(data, "createFavorite")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["favorite"])
        return item

    async def update_favorite(
        self,
        id: str,
        token: Optional[str],
        viewId: Optional[str] = None,
        companyId: Optional[str] = None,
        personId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if viewId is not None:
            attrs["viewId"] = viewId
        if companyId is not None:
            attrs["companyId"] = companyId
        if personId is not None:
            attrs["personId"] = personId
        data = await self.patch(f"favorites/{id}", token, json=attrs)
        item = self._extract_single(data, "updateFavorite")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["favorite"])
        return item

    async def update_many_favorites(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        viewId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if viewId is not None:
            attrs["viewId"] = viewId
        data = await self.patch("favorites", token, params=params, json=attrs)
        return data.get("data", {}).get("updateFavorites", [])

    async def delete_favorite_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"favorites/{id}", token)

    async def delete_many_favorites(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("favorites", token, params=params)
        return data.get("data", {}).get("deleteFavorites", [])

    # =============================================================================
    # workflows
    # =============================================================================

    async def get_all_workflows(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("workflows", token)
        items = self._extract_list(data, "workflows")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["workflow"])
        return items

    async def get_workflow_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"workflows/{id}", token)
        item = self._extract_single(data, "workflow")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["workflow"])
        return item

    async def create_workflow(
        self,
        token: Optional[str],
        name: str,
        statuses: Optional[list[str]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"name": name}
        if statuses is not None:
            attrs["statuses"] = statuses
        data = await self.post("workflows", token, json=attrs)
        item = self._extract_single(data, "createWorkflow")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflow"])
        return item

    async def update_workflow(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        statuses: Optional[list[str]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if statuses is not None:
            attrs["statuses"] = statuses
        data = await self.patch(f"workflows/{id}", token, json=attrs)
        item = self._extract_single(data, "updateWorkflow")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflow"])
        return item

    async def update_many_workflows(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if statuses is not None:
            attrs["statuses"] = statuses
        data = await self.patch("workflows", token, params=params, json=attrs)
        return data.get("data", {}).get("updateWorkflows", [])

    async def delete_workflow_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"workflows/{id}", token)

    async def delete_many_workflows(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("workflows", token, params=params)
        return data.get("data", {}).get("deleteWorkflows", [])

    # =============================================================================
    # workflowVersions
    # =============================================================================

    async def get_all_workflowVersions(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("workflowVersions", token)
        items = self._extract_list(data, "workflowVersions")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["workflowVersion"])
        return items

    async def get_workflowVersion_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"workflowVersions/{id}", token)
        item = self._extract_single(data, "workflowVersion")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["workflowVersion"])
        return item

    async def create_workflowVersion(
        self,
        token: Optional[str],
        workflowId: str,
        name: Optional[str] = None,
        trigger: Optional[dict[str, Any]] = None,
        steps: Optional[list[Any]] = None,
        status: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"workflowId": workflowId}
        if name is not None:
            attrs["name"] = name
        if trigger is not None:
            attrs["trigger"] = trigger
        if steps is not None:
            attrs["steps"] = steps
        if status is not None:
            attrs["status"] = status
        data = await self.post("workflowVersions", token, json=attrs)
        item = self._extract_single(data, "createWorkflowVersion")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflowVersion"])
        return item

    async def update_workflowVersion(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        trigger: Optional[dict[str, Any]] = None,
        steps: Optional[list[Any]] = None,
        status: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if trigger is not None:
            attrs["trigger"] = trigger
        if steps is not None:
            attrs["steps"] = steps
        if status is not None:
            attrs["status"] = status
        data = await self.patch(f"workflowVersions/{id}", token, json=attrs)
        item = self._extract_single(data, "updateWorkflowVersion")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflowVersion"])
        return item

    async def update_many_workflowVersions(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        status: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if status is not None:
            attrs["status"] = status
        data = await self.patch("workflowVersions", token, params=params, json=attrs)
        return data.get("data", {}).get("updateWorkflowVersions", [])

    async def delete_workflowVersion_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"workflowVersions/{id}", token)

    async def delete_many_workflowVersions(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("workflowVersions", token, params=params)
        return data.get("data", {}).get("deleteWorkflowVersions", [])

    # =============================================================================
    # workflowRuns
    # =============================================================================

    async def get_all_workflowRuns(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("workflowRuns", token)
        items = self._extract_list(data, "workflowRuns")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["workflowRun"])
        return items

    async def get_workflowRun_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"workflowRuns/{id}", token)
        item = self._extract_single(data, "workflowRun")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["workflowRun"])
        return item

    async def create_workflowRun(
        self,
        token: Optional[str],
        workflowId: str,
        workflowVersionId: Optional[str] = None,
        status: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"workflowId": workflowId}
        if workflowVersionId is not None:
            attrs["workflowVersionId"] = workflowVersionId
        if status is not None:
            attrs["status"] = status
        data = await self.post("workflowRuns", token, json=attrs)
        item = self._extract_single(data, "createWorkflowRun")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflowRun"])
        return item

    async def update_workflowRun(
        self,
        id: str,
        token: Optional[str],
        status: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if status is not None:
            attrs["status"] = status
        data = await self.patch(f"workflowRuns/{id}", token, json=attrs)
        item = self._extract_single(data, "updateWorkflowRun")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflowRun"])
        return item

    async def update_many_workflowRuns(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        status: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if status is not None:
            attrs["status"] = status
        data = await self.patch("workflowRuns", token, params=params, json=attrs)
        return data.get("data", {}).get("updateWorkflowRuns", [])

    async def delete_workflowRun_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"workflowRuns/{id}", token)

    async def delete_many_workflowRuns(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("workflowRuns", token, params=params)
        return data.get("data", {}).get("deleteWorkflowRuns", [])

    # =============================================================================
    # workflowAutomatedTriggers
    # =============================================================================

    async def get_all_workflowAutomatedTriggers(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("workflowAutomatedTriggers", token)
        items = self._extract_list(data, "workflowAutomatedTriggers")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["workflowAutomatedTrigger"])
        return items

    async def get_workflowAutomatedTrigger_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"workflowAutomatedTriggers/{id}", token)
        item = self._extract_single(data, "workflowAutomatedTrigger")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["workflowAutomatedTrigger"])
        return item

    async def create_workflowAutomatedTrigger(
        self,
        token: Optional[str],
        type: str,
        workflowId: Optional[str] = None,
        settings: Optional[dict[str, Any]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"type": type}
        if workflowId is not None:
            attrs["workflowId"] = workflowId
        if settings is not None:
            attrs["settings"] = settings
        data = await self.post("workflowAutomatedTriggers", token, json=attrs)
        item = self._extract_single(data, "createWorkflowAutomatedTrigger")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflowAutomatedTrigger"])
        return item

    async def update_workflowAutomatedTrigger(
        self,
        id: str,
        token: Optional[str],
        type: Optional[str] = None,
        settings: Optional[dict[str, Any]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if type is not None:
            attrs["type"] = type
        if settings is not None:
            attrs["settings"] = settings
        data = await self.patch(f"workflowAutomatedTriggers/{id}", token, json=attrs)
        item = self._extract_single(data, "updateWorkflowAutomatedTrigger")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["workflowAutomatedTrigger"])
        return item

    async def update_many_workflowAutomatedTriggers(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        type: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if type is not None:
            attrs["type"] = type
        data = await self.patch("workflowAutomatedTriggers", token, params=params, json=attrs)
        return data.get("data", {}).get("updateWorkflowAutomatedTriggers", [])

    async def delete_workflowAutomatedTrigger_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"workflowAutomatedTriggers/{id}", token)

    async def delete_many_workflowAutomatedTriggers(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("workflowAutomatedTriggers", token, params=params)
        return data.get("data", {}).get("deleteWorkflowAutomatedTriggers", [])

    # =============================================================================
    # calendarEvents
    # =============================================================================

    async def get_all_calendarEvents(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("calendarEvents", token)
        items = self._extract_list(data, "calendarEvents")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["calendarEvent"])
        return items

    async def get_calendarEvent_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"calendarEvents/{id}", token)
        item = self._extract_single(data, "calendarEvent")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["calendarEvent"])
        return item

    async def create_calendarEvent(
        self,
        token: Optional[str],
        title: str,
        startsAt: Optional[str] = None,
        endsAt: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        isFullDay: Optional[bool] = None,
        isCanceled: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"title": title}
        if startsAt is not None:
            attrs["startsAt"] = _normalize_datetime(startsAt)
        if endsAt is not None:
            attrs["endsAt"] = _normalize_datetime(endsAt)
        if description is not None:
            attrs["description"] = description
        if location is not None:
            attrs["location"] = location
        if isFullDay is not None:
            attrs["isFullDay"] = isFullDay
        if isCanceled is not None:
            attrs["isCanceled"] = isCanceled
        data = await self.post("calendarEvents", token, json=attrs)
        item = self._extract_single(data, "createCalendarEvent")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarEvent"])
        return item

    async def update_calendarEvent(
        self,
        id: str,
        token: Optional[str],
        title: Optional[str] = None,
        startsAt: Optional[str] = None,
        endsAt: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        isFullDay: Optional[bool] = None,
        isCanceled: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if title is not None:
            attrs["title"] = title
        if startsAt is not None:
            attrs["startsAt"] = _normalize_datetime(startsAt)
        if endsAt is not None:
            attrs["endsAt"] = _normalize_datetime(endsAt)
        if description is not None:
            attrs["description"] = description
        if location is not None:
            attrs["location"] = location
        if isFullDay is not None:
            attrs["isFullDay"] = isFullDay
        if isCanceled is not None:
            attrs["isCanceled"] = isCanceled
        data = await self.patch(f"calendarEvents/{id}", token, json=attrs)
        item = self._extract_single(data, "updateCalendarEvent")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarEvent"])
        return item

    async def update_many_calendarEvents(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        isCanceled: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if isCanceled is not None:
            attrs["isCanceled"] = isCanceled
        data = await self.patch("calendarEvents", token, params=params, json=attrs)
        return data.get("data", {}).get("updateCalendarEvents", [])

    async def delete_calendarEvent_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"calendarEvents/{id}", token)

    async def delete_many_calendarEvents(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("calendarEvents", token, params=params)
        return data.get("data", {}).get("deleteCalendarEvents", [])

    # =============================================================================
    # calendarChannels
    # =============================================================================

    async def get_all_calendarChannels(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("calendarChannels", token)
        items = self._extract_list(data, "calendarChannels")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["calendarChannel"])
        return items

    async def get_calendarChannel_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"calendarChannels/{id}", token)
        item = self._extract_single(data, "calendarChannel")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["calendarChannel"])
        return item

    async def create_calendarChannel(
        self,
        token: Optional[str],
        handle: Optional[str] = None,
        type: Optional[str] = None,
        visibility: Optional[str] = None,
        isContactAutoCreationEnabled: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if type is not None:
            attrs["type"] = type
        if visibility is not None:
            attrs["visibility"] = visibility
        if isContactAutoCreationEnabled is not None:
            attrs["isContactAutoCreationEnabled"] = isContactAutoCreationEnabled
        data = await self.post("calendarChannels", token, json=attrs)
        item = self._extract_single(data, "createCalendarChannel")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarChannel"])
        return item

    async def update_calendarChannel(
        self,
        id: str,
        token: Optional[str],
        handle: Optional[str] = None,
        visibility: Optional[str] = None,
        isContactAutoCreationEnabled: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if visibility is not None:
            attrs["visibility"] = visibility
        if isContactAutoCreationEnabled is not None:
            attrs["isContactAutoCreationEnabled"] = isContactAutoCreationEnabled
        data = await self.patch(f"calendarChannels/{id}", token, json=attrs)
        item = self._extract_single(data, "updateCalendarChannel")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarChannel"])
        return item

    async def update_many_calendarChannels(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        visibility: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if visibility is not None:
            attrs["visibility"] = visibility
        data = await self.patch("calendarChannels", token, params=params, json=attrs)
        return data.get("data", {}).get("updateCalendarChannels", [])

    async def delete_calendarChannel_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"calendarChannels/{id}", token)

    async def delete_many_calendarChannels(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("calendarChannels", token, params=params)
        return data.get("data", {}).get("deleteCalendarChannels", [])

    # =============================================================================
    # calendarChannelEventAssociations
    # =============================================================================

    async def get_all_calendarChannelEventAssociations(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("calendarChannelEventAssociations", token)
        items = self._extract_list(data, "calendarChannelEventAssociations")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["calendarChannelEventAssociation"])
        return items

    async def get_calendarChannelEventAssociation_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"calendarChannelEventAssociations/{id}", token)
        item = self._extract_single(data, "calendarChannelEventAssociation")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["calendarChannelEventAssociation"])
        return item

    async def create_calendarChannelEventAssociation(
        self,
        token: Optional[str],
        calendarChannelId: str,
        calendarEventId: str,
        eventExternalId: Optional[str] = None,
        recurringEventExternalId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "calendarChannelId": calendarChannelId,
            "calendarEventId": calendarEventId,
        }
        if eventExternalId is not None:
            attrs["eventExternalId"] = eventExternalId
        if recurringEventExternalId is not None:
            attrs["recurringEventExternalId"] = recurringEventExternalId
        data = await self.post("calendarChannelEventAssociations", token, json=attrs)
        item = self._extract_single(data, "createCalendarChannelEventAssociation")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarChannelEventAssociation"])
        return item

    async def update_calendarChannelEventAssociation(
        self,
        id: str,
        token: Optional[str],
        eventExternalId: Optional[str] = None,
        recurringEventExternalId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if eventExternalId is not None:
            attrs["eventExternalId"] = eventExternalId
        if recurringEventExternalId is not None:
            attrs["recurringEventExternalId"] = recurringEventExternalId
        data = await self.patch(f"calendarChannelEventAssociations/{id}", token, json=attrs)
        item = self._extract_single(data, "updateCalendarChannelEventAssociation")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarChannelEventAssociation"])
        return item

    async def update_many_calendarChannelEventAssociations(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        eventExternalId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if eventExternalId is not None:
            attrs["eventExternalId"] = eventExternalId
        data = await self.patch("calendarChannelEventAssociations", token, params=params, json=attrs)
        return data.get("data", {}).get("updateCalendarChannelEventAssociations", [])

    async def delete_calendarChannelEventAssociation_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"calendarChannelEventAssociations/{id}", token)

    async def delete_many_calendarChannelEventAssociations(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("calendarChannelEventAssociations", token, params=params)
        return data.get("data", {}).get("deleteCalendarChannelEventAssociations", [])

    # =============================================================================
    # calendarEventParticipants
    # =============================================================================

    async def get_all_calendarEventParticipants(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("calendarEventParticipants", token)
        items = self._extract_list(data, "calendarEventParticipants")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["calendarEventParticipant"])
        return items

    async def get_calendarEventParticipant_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"calendarEventParticipants/{id}", token)
        item = self._extract_single(data, "calendarEventParticipant")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["calendarEventParticipant"])
        return item

    async def create_calendarEventParticipant(
        self,
        token: Optional[str],
        calendarEventId: str,
        handle: Optional[str] = None,
        displayName: Optional[str] = None,
        isOrganizer: Optional[bool] = None,
        responseStatus: Optional[str] = None,
        personId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"calendarEventId": calendarEventId}
        if handle is not None:
            attrs["handle"] = handle
        if displayName is not None:
            attrs["displayName"] = displayName
        if isOrganizer is not None:
            attrs["isOrganizer"] = isOrganizer
        if responseStatus is not None:
            attrs["responseStatus"] = responseStatus
        if personId is not None:
            attrs["personId"] = personId
        data = await self.post("calendarEventParticipants", token, json=attrs)
        item = self._extract_single(data, "createCalendarEventParticipant")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarEventParticipant"])
        return item

    async def update_calendarEventParticipant(
        self,
        id: str,
        token: Optional[str],
        handle: Optional[str] = None,
        displayName: Optional[str] = None,
        isOrganizer: Optional[bool] = None,
        responseStatus: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if displayName is not None:
            attrs["displayName"] = displayName
        if isOrganizer is not None:
            attrs["isOrganizer"] = isOrganizer
        if responseStatus is not None:
            attrs["responseStatus"] = responseStatus
        data = await self.patch(f"calendarEventParticipants/{id}", token, json=attrs)
        item = self._extract_single(data, "updateCalendarEventParticipant")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["calendarEventParticipant"])
        return item

    async def update_many_calendarEventParticipants(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        responseStatus: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if responseStatus is not None:
            attrs["responseStatus"] = responseStatus
        data = await self.patch("calendarEventParticipants", token, params=params, json=attrs)
        return data.get("data", {}).get("updateCalendarEventParticipants", [])

    async def delete_calendarEventParticipant_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"calendarEventParticipants/{id}", token)

    async def delete_many_calendarEventParticipants(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("calendarEventParticipants", token, params=params)
        return data.get("data", {}).get("deleteCalendarEventParticipants", [])

    # =============================================================================
    # messages
    # =============================================================================

    async def get_all_messages(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("messages", token)
        items = self._extract_list(data, "messages")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["message"])
        return items

    async def get_message_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"messages/{id}", token)
        item = self._extract_single(data, "message")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["message"])
        return item

    async def create_message(
        self,
        token: Optional[str],
        text: Optional[str] = None,
        subject: Optional[str] = None,
        headerMessageId: Optional[str] = None,
        messageThreadId: Optional[str] = None,
        receivedAt: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if text is not None:
            attrs["text"] = text
        if subject is not None:
            attrs["subject"] = subject
        if headerMessageId is not None:
            attrs["headerMessageId"] = headerMessageId
        if messageThreadId is not None:
            attrs["messageThreadId"] = messageThreadId
        if receivedAt is not None:
            attrs["receivedAt"] = _normalize_datetime(receivedAt)
        data = await self.post("messages", token, json=attrs)
        item = self._extract_single(data, "createMessage")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["message"])
        return item

    async def update_message(
        self,
        id: str,
        token: Optional[str],
        text: Optional[str] = None,
        subject: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if text is not None:
            attrs["text"] = text
        if subject is not None:
            attrs["subject"] = subject
        data = await self.patch(f"messages/{id}", token, json=attrs)
        item = self._extract_single(data, "updateMessage")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["message"])
        return item

    async def update_many_messages(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        subject: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if subject is not None:
            attrs["subject"] = subject
        data = await self.patch("messages", token, params=params, json=attrs)
        return data.get("data", {}).get("updateMessages", [])

    async def delete_message_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"messages/{id}", token)

    async def delete_many_messages(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("messages", token, params=params)
        return data.get("data", {}).get("deleteMessages", [])

    # =============================================================================
    # messageThreads
    # =============================================================================

    async def get_all_messageThreads(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("messageThreads", token)
        items = self._extract_list(data, "messageThreads")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["messageThread"])
        return items

    async def get_messageThread_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"messageThreads/{id}", token)
        item = self._extract_single(data, "messageThread")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["messageThread"])
        return item

    async def create_messageThread(
        self,
        token: Optional[str],
        subject: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if subject is not None:
            attrs["subject"] = subject
        data = await self.post("messageThreads", token, json=attrs)
        item = self._extract_single(data, "createMessageThread")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageThread"])
        return item

    async def update_messageThread(
        self,
        id: str,
        token: Optional[str],
        subject: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if subject is not None:
            attrs["subject"] = subject
        data = await self.patch(f"messageThreads/{id}", token, json=attrs)
        item = self._extract_single(data, "updateMessageThread")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageThread"])
        return item

    async def update_many_messageThreads(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        subject: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if subject is not None:
            attrs["subject"] = subject
        data = await self.patch("messageThreads", token, params=params, json=attrs)
        return data.get("data", {}).get("updateMessageThreads", [])

    async def delete_messageThread_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"messageThreads/{id}", token)

    async def delete_many_messageThreads(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("messageThreads", token, params=params)
        return data.get("data", {}).get("deleteMessageThreads", [])

    # =============================================================================
    # messageChannels
    # =============================================================================

    async def get_all_messageChannels(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("messageChannels", token)
        items = self._extract_list(data, "messageChannels")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["messageChannel"])
        return items

    async def get_messageChannel_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"messageChannels/{id}", token)
        item = self._extract_single(data, "messageChannel")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["messageChannel"])
        return item

    async def create_messageChannel(
        self,
        token: Optional[str],
        handle: Optional[str] = None,
        type: Optional[str] = None,
        visibility: Optional[str] = None,
        isContactAutoCreationEnabled: Optional[bool] = None,
        connectedAccountId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if type is not None:
            attrs["type"] = type
        if visibility is not None:
            attrs["visibility"] = visibility
        if isContactAutoCreationEnabled is not None:
            attrs["isContactAutoCreationEnabled"] = isContactAutoCreationEnabled
        if connectedAccountId is not None:
            attrs["connectedAccountId"] = connectedAccountId
        data = await self.post("messageChannels", token, json=attrs)
        item = self._extract_single(data, "createMessageChannel")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageChannel"])
        return item

    async def update_messageChannel(
        self,
        id: str,
        token: Optional[str],
        handle: Optional[str] = None,
        visibility: Optional[str] = None,
        isSyncEnabled: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if visibility is not None:
            attrs["visibility"] = visibility
        if isSyncEnabled is not None:
            attrs["isSyncEnabled"] = isSyncEnabled
        data = await self.patch(f"messageChannels/{id}", token, json=attrs)
        item = self._extract_single(data, "updateMessageChannel")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageChannel"])
        return item

    async def update_many_messageChannels(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        visibility: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if visibility is not None:
            attrs["visibility"] = visibility
        data = await self.patch("messageChannels", token, params=params, json=attrs)
        return data.get("data", {}).get("updateMessageChannels", [])

    async def delete_messageChannel_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"messageChannels/{id}", token)

    async def delete_many_messageChannels(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("messageChannels", token, params=params)
        return data.get("data", {}).get("deleteMessageChannels", [])

    # =============================================================================
    # messageParticipants
    # =============================================================================

    async def get_all_messageParticipants(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("messageParticipants", token)
        items = self._extract_list(data, "messageParticipants")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["messageParticipant"])
        return items

    async def get_messageParticipant_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"messageParticipants/{id}", token)
        item = self._extract_single(data, "messageParticipant")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["messageParticipant"])
        return item

    async def create_messageParticipant(
        self,
        token: Optional[str],
        messageId: str,
        role: Optional[str] = None,
        handle: Optional[str] = None,
        displayName: Optional[str] = None,
        personId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"messageId": messageId}
        if role is not None:
            attrs["role"] = role
        if handle is not None:
            attrs["handle"] = handle
        if displayName is not None:
            attrs["displayName"] = displayName
        if personId is not None:
            attrs["personId"] = personId
        data = await self.post("messageParticipants", token, json=attrs)
        item = self._extract_single(data, "createMessageParticipant")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageParticipant"])
        return item

    async def update_messageParticipant(
        self,
        id: str,
        token: Optional[str],
        role: Optional[str] = None,
        handle: Optional[str] = None,
        displayName: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if role is not None:
            attrs["role"] = role
        if handle is not None:
            attrs["handle"] = handle
        if displayName is not None:
            attrs["displayName"] = displayName
        data = await self.patch(f"messageParticipants/{id}", token, json=attrs)
        item = self._extract_single(data, "updateMessageParticipant")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageParticipant"])
        return item

    async def update_many_messageParticipants(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        role: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if role is not None:
            attrs["role"] = role
        data = await self.patch("messageParticipants", token, params=params, json=attrs)
        return data.get("data", {}).get("updateMessageParticipants", [])

    async def delete_messageParticipant_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"messageParticipants/{id}", token)

    async def delete_many_messageParticipants(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("messageParticipants", token, params=params)
        return data.get("data", {}).get("deleteMessageParticipants", [])

    # =============================================================================
    # messageFolders
    # =============================================================================

    async def get_all_messageFolders(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("messageFolders", token)
        items = self._extract_list(data, "messageFolders")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["messageFolder"])
        return items

    async def get_messageFolder_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"messageFolders/{id}", token)
        item = self._extract_single(data, "messageFolder")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["messageFolder"])
        return item

    async def create_messageFolder(
        self,
        token: Optional[str],
        name: Optional[str] = None,
        messageChannelId: Optional[str] = None,
        isSentFolder: Optional[bool] = None,
        isSynced: Optional[bool] = None,
        pendingSyncAction: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if messageChannelId is not None:
            attrs["messageChannelId"] = messageChannelId
        if isSentFolder is not None:
            attrs["isSentFolder"] = isSentFolder
        if isSynced is not None:
            attrs["isSynced"] = isSynced
        if pendingSyncAction is not None:
            attrs["pendingSyncAction"] = pendingSyncAction
        data = await self.post("messageFolders", token, json=attrs)
        item = self._extract_single(data, "createMessageFolder")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageFolder"])
        return item

    async def update_messageFolder(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        isSynced: Optional[bool] = None,
        pendingSyncAction: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if isSynced is not None:
            attrs["isSynced"] = isSynced
        if pendingSyncAction is not None:
            attrs["pendingSyncAction"] = pendingSyncAction
        data = await self.patch(f"messageFolders/{id}", token, json=attrs)
        item = self._extract_single(data, "updateMessageFolder")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageFolder"])
        return item

    async def update_many_messageFolders(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        isSynced: Optional[bool] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if isSynced is not None:
            attrs["isSynced"] = isSynced
        data = await self.patch("messageFolders", token, params=params, json=attrs)
        return data.get("data", {}).get("updateMessageFolders", [])

    async def delete_messageFolder_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"messageFolders/{id}", token)

    async def delete_many_messageFolders(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("messageFolders", token, params=params)
        return data.get("data", {}).get("deleteMessageFolders", [])

    # =============================================================================
    # messageChannelMessageAssociations
    # =============================================================================

    async def get_all_messageChannelMessageAssociations(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("messageChannelMessageAssociations", token)
        items = self._extract_list(data, "messageChannelMessageAssociations")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["messageChannelMessageAssociation"])
        return items

    async def get_messageChannelMessageAssociation_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"messageChannelMessageAssociations/{id}", token)
        item = self._extract_single(data, "messageChannelMessageAssociation")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["messageChannelMessageAssociation"])
        return item

    async def create_messageChannelMessageAssociation(
        self,
        token: Optional[str],
        messageChannelId: str,
        messageId: str,
        direction: Optional[str] = None,
        messageThreadId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "messageChannelId": messageChannelId,
            "messageId": messageId,
        }
        if direction is not None:
            attrs["direction"] = direction
        if messageThreadId is not None:
            attrs["messageThreadId"] = messageThreadId
        data = await self.post("messageChannelMessageAssociations", token, json=attrs)
        item = self._extract_single(data, "createMessageChannelMessageAssociation")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageChannelMessageAssociation"])
        return item

    async def update_messageChannelMessageAssociation(
        self,
        id: str,
        token: Optional[str],
        direction: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if direction is not None:
            attrs["direction"] = direction
        data = await self.patch(f"messageChannelMessageAssociations/{id}", token, json=attrs)
        item = self._extract_single(data, "updateMessageChannelMessageAssociation")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["messageChannelMessageAssociation"])
        return item

    async def update_many_messageChannelMessageAssociations(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        direction: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if direction is not None:
            attrs["direction"] = direction
        data = await self.patch("messageChannelMessageAssociations", token, params=params, json=attrs)
        return data.get("data", {}).get("updateMessageChannelMessageAssociations", [])

    async def delete_messageChannelMessageAssociation_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"messageChannelMessageAssociations/{id}", token)

    async def delete_many_messageChannelMessageAssociations(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("messageChannelMessageAssociations", token, params=params)
        return data.get("data", {}).get("deleteMessageChannelMessageAssociations", [])

    # =============================================================================
    # noteTargets
    # =============================================================================

    async def get_all_noteTargets(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("noteTargets", token)
        items = self._extract_list(data, "noteTargets")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["noteTarget"])
        return items

    async def get_noteTarget_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"noteTargets/{id}", token)
        item = self._extract_single(data, "noteTarget")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["noteTarget"])
        return item

    async def create_noteTarget(
        self,
        token: Optional[str],
        noteId: str,
        personId: Optional[str] = None,
        companyId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"noteId": noteId}
        if personId is not None:
            attrs["personId"] = personId
        if companyId is not None:
            attrs["companyId"] = companyId
        if opportunityId is not None:
            attrs["opportunityId"] = opportunityId
        data = await self.post("noteTargets", token, json=attrs)
        item = self._extract_single(data, "createNoteTarget")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["noteTarget"])
        return item

    async def update_noteTarget(
        self,
        id: str,
        token: Optional[str],
        personId: Optional[str] = None,
        companyId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if personId is not None:
            attrs["personId"] = personId
        if companyId is not None:
            attrs["companyId"] = companyId
        if opportunityId is not None:
            attrs["opportunityId"] = opportunityId
        data = await self.patch(f"noteTargets/{id}", token, json=attrs)
        item = self._extract_single(data, "updateNoteTarget")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["noteTarget"])
        return item

    async def update_many_noteTargets(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        personId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if personId is not None:
            attrs["personId"] = personId
        data = await self.patch("noteTargets", token, params=params, json=attrs)
        return data.get("data", {}).get("updateNoteTargets", [])

    async def delete_noteTarget_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"noteTargets/{id}", token)

    async def delete_many_noteTargets(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("noteTargets", token, params=params)
        return data.get("data", {}).get("deleteNoteTargets", [])

    # =============================================================================
    # taskTargets
    # =============================================================================

    async def get_all_taskTargets(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("taskTargets", token)
        items = self._extract_list(data, "taskTargets")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["taskTarget"])
        return items

    async def get_taskTarget_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"taskTargets/{id}", token)
        item = self._extract_single(data, "taskTarget")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["taskTarget"])
        return item

    async def create_taskTarget(
        self,
        token: Optional[str],
        taskId: str,
        personId: Optional[str] = None,
        companyId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"taskId": taskId}
        if personId is not None:
            attrs["personId"] = personId
        if companyId is not None:
            attrs["companyId"] = companyId
        if opportunityId is not None:
            attrs["opportunityId"] = opportunityId
        data = await self.post("taskTargets", token, json=attrs)
        item = self._extract_single(data, "createTaskTarget")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["taskTarget"])
        return item

    async def update_taskTarget(
        self,
        id: str,
        token: Optional[str],
        personId: Optional[str] = None,
        companyId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if personId is not None:
            attrs["personId"] = personId
        if companyId is not None:
            attrs["companyId"] = companyId
        if opportunityId is not None:
            attrs["opportunityId"] = opportunityId
        data = await self.patch(f"taskTargets/{id}", token, json=attrs)
        item = self._extract_single(data, "updateTaskTarget")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["taskTarget"])
        return item

    async def update_many_taskTargets(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        personId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if personId is not None:
            attrs["personId"] = personId
        data = await self.patch("taskTargets", token, params=params, json=attrs)
        return data.get("data", {}).get("updateTaskTargets", [])

    async def delete_taskTarget_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"taskTargets/{id}", token)

    async def delete_many_taskTargets(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("taskTargets", token, params=params)
        return data.get("data", {}).get("deleteTaskTargets", [])

    # =============================================================================
    # timelineActivities
    # =============================================================================

    async def get_all_timelineActivities(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("timelineActivities", token)
        items = self._extract_list(data, "timelineActivities")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["timelineActivity"])
        return items

    async def get_timelineActivity_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"timelineActivities/{id}", token)
        item = self._extract_single(data, "timelineActivity")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["timelineActivity"])
        return item

    async def create_timelineActivity(
        self,
        token: Optional[str],
        name: str,
        happensAt: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        workspaceMemberId: Optional[str] = None,
        personId: Optional[str] = None,
        companyId: Optional[str] = None,
        opportunityId: Optional[str] = None,
        noteId: Optional[str] = None,
        taskId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"name": name}
        if happensAt is not None:
            attrs["happensAt"] = _normalize_datetime(happensAt)
        if properties is not None:
            attrs["properties"] = properties
        if workspaceMemberId is not None:
            attrs["workspaceMemberId"] = workspaceMemberId
        if personId is not None:
            attrs["personId"] = personId
        if companyId is not None:
            attrs["companyId"] = companyId
        if opportunityId is not None:
            attrs["opportunityId"] = opportunityId
        if noteId is not None:
            attrs["noteId"] = noteId
        if taskId is not None:
            attrs["taskId"] = taskId
        data = await self.post("timelineActivities", token, json=attrs)
        item = self._extract_single(data, "createTimelineActivity")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["timelineActivity"])
        return item

    async def update_timelineActivity(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        if properties is not None:
            attrs["properties"] = properties
        data = await self.patch(f"timelineActivities/{id}", token, json=attrs)
        item = self._extract_single(data, "updateTimelineActivity")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["timelineActivity"])
        return item

    async def update_many_timelineActivities(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        properties: Optional[dict[str, Any]] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if properties is not None:
            attrs["properties"] = properties
        data = await self.patch("timelineActivities", token, params=params, json=attrs)
        return data.get("data", {}).get("updateTimelineActivities", [])

    async def delete_timelineActivity_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"timelineActivities/{id}", token)

    async def delete_many_timelineActivities(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("timelineActivities", token, params=params)
        return data.get("data", {}).get("deleteTimelineActivities", [])

    # =============================================================================
    # workspaceMembers
    # =============================================================================

    async def get_all_workspaceMembers(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("workspaceMembers", token)
        items = self._extract_list(data, "workspaceMembers")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["workspaceMember"])
        return items

    async def get_workspaceMember_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"workspaceMembers/{id}", token)
        item = self._extract_single(data, "workspaceMember")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["workspaceMember"])
        return item

    async def delete_workspaceMember_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"workspaceMembers/{id}", token)

    # =============================================================================
    # connectedAccounts
    # =============================================================================

    async def get_all_connectedAccounts(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("connectedAccounts", token)
        items = self._extract_list(data, "connectedAccounts")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["connectedAccount"])
        return items

    async def get_connectedAccount_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"connectedAccounts/{id}", token)
        item = self._extract_single(data, "connectedAccount")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["connectedAccount"])
        return item

    async def create_connectedAccount(
        self,
        token: Optional[str],
        handle: str,
        provider: str,
        accessToken: Optional[str] = None,
        refreshToken: Optional[str] = None,
        visibility: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {"handle": handle, "provider": provider}
        if accessToken is not None:
            attrs["accessToken"] = accessToken
        if refreshToken is not None:
            attrs["refreshToken"] = refreshToken
        if visibility is not None:
            attrs["visibility"] = visibility
        data = await self.post("connectedAccounts", token, json=attrs)
        item = self._extract_single(data, "createConnectedAccount")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["connectedAccount"])
        return item

    async def update_connectedAccount(
        self,
        id: str,
        token: Optional[str],
        handle: Optional[str] = None,
        visibility: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if visibility is not None:
            attrs["visibility"] = visibility
        data = await self.patch(f"connectedAccounts/{id}", token, json=attrs)
        item = self._extract_single(data, "updateConnectedAccount")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["connectedAccount"])
        return item

    async def update_many_connectedAccounts(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        visibility: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if visibility is not None:
            attrs["visibility"] = visibility
        data = await self.patch("connectedAccounts", token, params=params, json=attrs)
        return data.get("data", {}).get("updateConnectedAccounts", [])

    async def delete_connectedAccount_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"connectedAccounts/{id}", token)

    async def delete_many_connectedAccounts(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("connectedAccounts", token, params=params)
        return data.get("data", {}).get("deleteConnectedAccounts", [])

    # =============================================================================
    # favoriteFolders
    # =============================================================================

    async def get_all_favoriteFolders(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("favoriteFolders", token)
        items = self._extract_list(data, "favoriteFolders")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["favoriteFolder"])
        return items

    async def get_favoriteFolder_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"favoriteFolders/{id}", token)
        item = self._extract_single(data, "favoriteFolder")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["favoriteFolder"])
        return item

    async def create_favoriteFolder(
        self,
        token: Optional[str],
        name: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        data = await self.post("favoriteFolders", token, json=attrs)
        item = self._extract_single(data, "createFavoriteFolder")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["favoriteFolder"])
        return item

    async def update_favoriteFolder(
        self,
        id: str,
        token: Optional[str],
        name: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if name is not None:
            attrs["name"] = name
        data = await self.patch(f"favoriteFolders/{id}", token, json=attrs)
        item = self._extract_single(data, "updateFavoriteFolder")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["favoriteFolder"])
        return item

    async def update_many_favoriteFolders(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        name: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if name is not None:
            attrs["name"] = name
        data = await self.patch("favoriteFolders", token, params=params, json=attrs)
        return data.get("data", {}).get("updateFavoriteFolders", [])

    async def delete_favoriteFolder_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"favoriteFolders/{id}", token)

    async def delete_many_favoriteFolders(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("favoriteFolders", token, params=params)
        return data.get("data", {}).get("deleteFavoriteFolders", [])

    # =============================================================================
    # dashboards
    # =============================================================================

    async def get_all_dashboards(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("dashboards", token)
        items = self._extract_list(data, "dashboards")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["dashboard"])
        return items

    async def get_dashboard_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"dashboards/{id}", token)
        item = self._extract_single(data, "dashboard")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["dashboard"])
        return item

    async def create_dashboard(
        self,
        token: Optional[str],
        title: Optional[str] = None,
        pageLayoutId: Optional[str] = None,
        position: Optional[int] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if title is not None:
            attrs["title"] = title
        if pageLayoutId is not None:
            attrs["pageLayoutId"] = pageLayoutId
        if position is not None:
            attrs["position"] = position
        data = await self.post("dashboards", token, json=attrs)
        item = self._extract_single(data, "createDashboard")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["dashboard"])
        return item

    async def update_dashboard(
        self,
        id: str,
        token: Optional[str],
        title: Optional[str] = None,
        pageLayoutId: Optional[str] = None,
        position: Optional[int] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if title is not None:
            attrs["title"] = title
        if pageLayoutId is not None:
            attrs["pageLayoutId"] = pageLayoutId
        if position is not None:
            attrs["position"] = position
        data = await self.patch(f"dashboards/{id}", token, json=attrs)
        item = self._extract_single(data, "updateDashboard")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["dashboard"])
        return item

    async def update_many_dashboards(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        title: Optional[str] = None,
        position: Optional[int] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if title is not None:
            attrs["title"] = title
        if position is not None:
            attrs["position"] = position
        data = await self.patch("dashboards", token, params=params, json=attrs)
        return data.get("data", {}).get("updateDashboards", [])

    async def delete_dashboard_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"dashboards/{id}", token)

    async def delete_many_dashboards(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("dashboards", token, params=params)
        return data.get("data", {}).get("deleteDashboards", [])

    # =============================================================================
    # blocklists
    # =============================================================================

    async def get_all_blocklists(
        self, token: Optional[str], include_all_fields: bool = False
    ) -> list[dict[str, Any]]:
        data = await self.get("blocklists", token)
        items = self._extract_list(data, "blocklists")
        if not include_all_fields and ALLOW_ALL_AGGREGATE:
            return _filter_fields(items, COMMON_FIELDS["blocklist"])
        return items

    async def get_blocklist_by_id(
        self, id: str, token: Optional[str], include_all_fields: bool = False
    ) -> dict[str, Any]:
        data = await self.get(f"blocklists/{id}", token)
        item = self._extract_single(data, "blocklist")
        if not include_all_fields:
            return _filter_fields(item, COMMON_FIELDS["blocklist"])
        return item

    async def create_blocklist(
        self,
        token: Optional[str],
        handle: Optional[str] = None,
        workspaceMemberId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if workspaceMemberId is not None:
            attrs["workspaceMemberId"] = workspaceMemberId
        data = await self.post("blocklists", token, json=attrs)
        item = self._extract_single(data, "createBlocklist")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["blocklist"])
        return item

    async def update_blocklist(
        self,
        id: str,
        token: Optional[str],
        handle: Optional[str] = None,
        workspaceMemberId: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if handle is not None:
            attrs["handle"] = handle
        if workspaceMemberId is not None:
            attrs["workspaceMemberId"] = workspaceMemberId
        data = await self.patch(f"blocklists/{id}", token, json=attrs)
        item = self._extract_single(data, "updateBlocklist")
        if not include_all_fields and not ALLOW_ALL_AGGREGATE:
            return _filter_fields(item, COMMON_FIELDS["blocklist"])
        return item

    async def update_many_blocklists(
        self,
        token: Optional[str],
        filter_id_in: Optional[list[str]] = None,
        handle: Optional[str] = None,
        include_all_fields: bool = False,
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        attrs = {}
        if handle is not None:
            attrs["handle"] = handle
        data = await self.patch("blocklists", token, params=params, json=attrs)
        return data.get("data", {}).get("updateBlocklists", [])

    async def delete_blocklist_by_id(
        self, id: str, token: Optional[str]
    ) -> dict[str, Any]:
        return await self.delete(f"blocklists/{id}", token)

    async def delete_many_blocklists(
        self, token: Optional[str], filter_id_in: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        params = {}
        if filter_id_in:
            params["filter"] = f"id[in]:[{','.join(filter_id_in)}]"
        data = await self.delete("blocklists", token, params=params)
        return data.get("data", {}).get("deleteBlocklists", [])