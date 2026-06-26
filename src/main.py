import os
import sys
import json
from contextvars import ContextVar
from typing import Any, Optional

from fastmcp import FastMCP, Context
from pydantic import BaseModel
from toon_mcp import json_to_toon

from .client import TwentyClient

_current_user_token: ContextVar[Optional[str]] = ContextVar(
    "current_user_token", default=None
)

ALLOW_ALL_AGGREGATE = os.getenv("ALLOW_ALL_AGGREGATE", "false").lower() in ("true", "1", "yes")


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                _current_user_token.set(token)
        await self.app(scope, receive, send)


mcp = FastMCP("twenty-mcp-server")

_client: Optional[TwentyClient] = None


def get_client() -> TwentyClient:
    global _client
    if _client is None:
        _client = TwentyClient()
    return _client


def get_user_token() -> Optional[str]:
    return _current_user_token.get()


# =============================================================================
# Pydantic Contract Models — Company
# =============================================================================
class CreateCompanyParam(BaseModel):
    name: str = ""
    domainName: str = ""
    address: str = ""
    linkedinLink: str = ""
    annualRevenue: str = ""
    accountOwnerId: str = ""
    position: int = 0


class UpdateCompanyParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    domainName: Optional[str] = None
    address: Optional[str] = None
    linkedinLink: Optional[str] = None
    annualRevenue: Optional[str] = None
    accountOwnerId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Person
# =============================================================================
class CreatePersonParam(BaseModel):
    name: str = ""
    emails: str = ""
    phones: str = ""
    jobTitle: str = ""
    linkedinLink: str = ""
    companyId: str = ""
    avatarUrl: str = ""
    position: int = 0


class UpdatePersonParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    emails: Optional[str] = None
    phones: Optional[str] = None
    jobTitle: Optional[str] = None
    linkedinLink: Optional[str] = None
    companyId: Optional[str] = None
    avatarUrl: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Opportunity
# =============================================================================
class CreateOpportunityParam(BaseModel):
    name: str = ""
    amount: str = ""
    closeDate: str = ""
    stage: str = ""
    companyId: str = ""
    pointOfContactId: str = ""
    ownerId: str = ""
    position: int = 0


class UpdateOpportunityParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[str] = None
    closeDate: Optional[str] = None
    stage: Optional[str] = None
    companyId: Optional[str] = None
    pointOfContactId: Optional[str] = None
    ownerId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Note
# =============================================================================
class CreateNoteParam(BaseModel):
    title: str = ""
    bodyV2: str = ""
    position: int = 0


class UpdateNoteParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    bodyV2: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Task
# =============================================================================
class CreateTaskParam(BaseModel):
    title: str = ""
    bodyV2: str = ""
    status: str = ""
    dueAt: str = ""
    assigneeId: str = ""
    position: int = 0


class UpdateTaskParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    bodyV2: Optional[str] = None
    status: Optional[str] = None
    dueAt: Optional[str] = None
    assigneeId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Workflow
# =============================================================================
class CreateWorkflowParam(BaseModel):
    name: str = ""
    statuses: str = "[]"
    lastPublishedVersionId: str = ""
    position: int = 0


class UpdateWorkflowParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    statuses: Optional[str] = None
    lastPublishedVersionId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — WorkspaceMember
# =============================================================================
class UpdateWorkspaceMemberParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    colorScheme: Optional[str] = None
    locale: Optional[str] = None
    avatarUrl: Optional[str] = None
    userEmail: Optional[str] = None
    calendarStartDay: Optional[int] = None
    timeZone: Optional[str] = None
    dateFormat: Optional[str] = None
    timeFormat: Optional[str] = None
    numberFormat: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Attachment
# =============================================================================
class CreateAttachmentParam(BaseModel):
    name: str = ""
    fullPath: str = ""
    fileCategory: str = ""
    authorId: str = ""
    targetTaskId: str = ""
    targetNoteId: str = ""
    targetPersonId: str = ""
    targetCompanyId: str = ""
    targetOpportunityId: str = ""
    targetDashboardId: str = ""
    targetWorkflowId: str = ""


class UpdateAttachmentParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    fullPath: Optional[str] = None
    type: Optional[str] = None
    fileCategory: Optional[str] = None
    authorId: Optional[str] = None
    targetTaskId: Optional[str] = None
    targetNoteId: Optional[str] = None
    targetPersonId: Optional[str] = None
    targetCompanyId: Optional[str] = None
    targetOpportunityId: Optional[str] = None
    targetDashboardId: Optional[str] = None
    targetWorkflowId: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — NoteTarget
# =============================================================================
class CreateNoteTargetParam(BaseModel):
    noteId: str = ""
    targetPersonId: str = ""
    targetCompanyId: str = ""
    targetOpportunityId: str = ""


class UpdateNoteTargetParam(BaseModel):
    id: Optional[str] = None
    noteId: Optional[str] = None
    targetPersonId: Optional[str] = None
    targetCompanyId: Optional[str] = None
    targetOpportunityId: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — TaskTarget
# =============================================================================
class CreateTaskTargetParam(BaseModel):
    taskId: str = ""
    targetPersonId: str = ""
    targetCompanyId: str = ""
    targetOpportunityId: str = ""


class UpdateTaskTargetParam(BaseModel):
    id: Optional[str] = None
    taskId: Optional[str] = None
    targetPersonId: Optional[str] = None
    targetCompanyId: Optional[str] = None
    targetOpportunityId: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — TimelineActivity
# =============================================================================
class CreateTimelineActivityParam(BaseModel):
    name: str = ""
    happensAt: str = ""
    workspaceMemberId: str = ""
    linkedRecordId: str = ""
    linkedObjectMetadataId: str = ""
    targetPersonId: str = ""
    targetCompanyId: str = ""
    targetOpportunityId: str = ""
    targetNoteId: str = ""
    targetTaskId: str = ""
    targetWorkflowId: str = ""
    targetWorkflowVersionId: str = ""
    targetWorkflowRunId: str = ""
    targetDashboardId: str = ""
    targetMessageListId: str = ""
    targetMessageCampaignId: str = ""
    properties: str = "{}"
    position: int = 0


class UpdateTimelineActivityParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    happensAt: Optional[str] = None
    workspaceMemberId: Optional[str] = None
    linkedRecordId: Optional[str] = None
    linkedObjectMetadataId: Optional[str] = None
    targetPersonId: Optional[str] = None
    targetCompanyId: Optional[str] = None
    targetOpportunityId: Optional[str] = None
    targetNoteId: Optional[str] = None
    targetTaskId: Optional[str] = None
    targetWorkflowId: Optional[str] = None
    targetWorkflowVersionId: Optional[str] = None
    targetWorkflowRunId: Optional[str] = None
    targetDashboardId: Optional[str] = None
    targetMessageListId: Optional[str] = None
    targetMessageCampaignId: Optional[str] = None
    properties: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — CalendarEvent
# =============================================================================
class CreateCalendarEventParam(BaseModel):
    title: str = ""
    isCanceled: bool = False
    isFullDay: bool = False
    startsAt: str = ""
    endsAt: str = ""
    description: str = ""
    location: str = ""
    iCalUid: str = ""
    conferenceSolution: str = ""
    conferenceLink: str = "{}"


class UpdateCalendarEventParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    isCanceled: Optional[bool] = None
    isFullDay: Optional[bool] = None
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    iCalUid: Optional[str] = None
    conferenceSolution: Optional[str] = None
    conferenceLink: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — CalendarEventParticipant
# =============================================================================
class CreateCalendarEventParticipantParam(BaseModel):
    calendarEventId: str = ""
    handle: str = ""
    displayName: str = ""
    isOrganizer: bool = False
    responseStatus: str = "NEEDS_ACTION"
    personId: str = ""
    workspaceMemberId: str = ""


class UpdateCalendarEventParticipantParam(BaseModel):
    id: Optional[str] = None
    calendarEventId: Optional[str] = None
    handle: Optional[str] = None
    displayName: Optional[str] = None
    isOrganizer: Optional[bool] = None
    responseStatus: Optional[str] = None
    personId: Optional[str] = None
    workspaceMemberId: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — Message
# =============================================================================
class CreateMessageParam(BaseModel):
    headerMessageId: str = ""
    subject: str = ""
    text: str = ""
    receivedAt: str = ""
    messageThreadId: str = ""
    messageCampaignId: str = ""
    deliveryStatus: str = ""


class UpdateMessageParam(BaseModel):
    id: Optional[str] = None
    headerMessageId: Optional[str] = None
    subject: Optional[str] = None
    text: Optional[str] = None
    receivedAt: Optional[str] = None
    messageThreadId: Optional[str] = None
    messageCampaignId: Optional[str] = None
    deliveryStatus: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — MessageThread
# =============================================================================
class CreateMessageThreadParam(BaseModel):
    subject: str = ""


class UpdateMessageThreadParam(BaseModel):
    id: Optional[str] = None
    subject: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — MessageParticipant
# =============================================================================
class CreateMessageParticipantParam(BaseModel):
    messageId: str = ""
    role: str = ""
    handle: str = ""
    displayName: str = ""
    personId: str = ""
    workspaceMemberId: str = ""
    messageCampaignId: str = ""


class UpdateMessageParticipantParam(BaseModel):
    id: Optional[str] = None
    messageId: Optional[str] = None
    role: Optional[str] = None
    handle: Optional[str] = None
    displayName: Optional[str] = None
    personId: Optional[str] = None
    workspaceMemberId: Optional[str] = None
    messageCampaignId: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — CallRecording
# =============================================================================
class CreateCallRecordingParam(BaseModel):
    title: str = ""
    status: str = ""
    recordingRequestStatus: str = ""
    applicationId: str = ""
    externalBotId: str = ""
    externalRecordingId: str = ""
    startedAt: str = ""
    endedAt: str = ""
    calendarEventId: str = ""


class UpdateCallRecordingParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    recordingRequestStatus: Optional[str] = None
    applicationId: Optional[str] = None
    externalBotId: Optional[str] = None
    externalRecordingId: Optional[str] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None
    calendarEventId: Optional[str] = None


# =============================================================================
# Helper to parse JSON string fields
# =============================================================================
def _parse_json_field(value: str) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


# Fields that must be omitted when empty/blank — the backend rejects empty strings
# for these composite, enum, UUID, or datetime fields
_MUST_OMIT_IF_EMPTY: set[str] = {
    # Composite JSON fields (expect dict/array, reject "")
    "address", "linkedinLink", "annualRevenue",
    "emails", "phones", "jobTitle",
    "amount", "closeDate", "bodyV2", "statuses", "location",
    "conferenceLink", "properties",
    # UUID fields that are optional but reject ""
    "noteId", "taskId", "companyId", "targetNoteId", "targetTaskId",
    "targetPersonId", "targetCompanyId", "targetOpportunityId",
    "authorId", "workspaceMemberId", "calendarEventId", "messageId",
    "messageThreadId", "headerMessageId", "messageCampaignId",
    "linkedRecordId", "linkedObjectMetadataId",
    "targetWorkflowId", "targetWorkflowVersionId", "targetWorkflowRunId",
    "targetDashboardId", "targetMessageListId", "targetMessageCampaignId",
    "personId", "applicationId", "externalBotId", "externalRecordingId",
    "recordingRequestStatus", "deliveryStatus",
    # Additional nullable UUID fields that reject empty string
    "accountOwnerId", "pointOfContactId", "assigneeId", "ownerId", "avatarUrl",
    "userEmail", "position",
    # Enum fields that reject ""
    "stage", "status", "fileCategory", "dateFormat", "timeFormat", "numberFormat",
    "currencyCode", "timeZone", "locale", "colorScheme",
    # Datetime fields that reject ""
    "startsAt", "endsAt", "dueAt", "receivedAt", "happensAt",
    "startedAt", "endedAt",
    # Non-nullable bool fields that reject None on update
    "isCanceled", "isFullDay",
}


def _build_payload(params: BaseModel) -> dict[str, Any]:
    payload = {}
    for k, v in params.model_dump(exclude_unset=True).items():
        if k == "id":
            continue
        if v is None:
            continue
        # Omit empty-string values for composite/enum/UUID/datetime fields
        if v == "" and k in _MUST_OMIT_IF_EMPTY:
            continue
        # Parse JSON strings for fields that expect objects/arrays
        if isinstance(v, str) and v.startswith("{"):
            parsed = _parse_json_field(v)
            if not parsed and k in _MUST_OMIT_IF_EMPTY:
                continue
            payload[k] = parsed
        elif isinstance(v, str) and v.startswith("["):
            parsed = _parse_json_field(v)
            if not parsed and k in _MUST_OMIT_IF_EMPTY:
                continue
            payload[k] = parsed
        else:
            payload[k] = v
    return payload


# =============================================================================
# Company Tools
# =============================================================================
@mcp.tool()
async def list_companies(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all company records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_companies(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_company_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single company by its ID.

    Args:
        id: The unique ID of the company (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_company_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_company(
    name: str = "",
    domainName: str = "",
    address: str = "",
    linkedinLink: str = "",
    annualRevenue: str = "",
    accountOwnerId: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new company record.

    Args:
        name: Name of the company.
        domainName: JSON string with primaryLinkUrl and primaryLinkLabel.
        address: JSON string with address fields.
        linkedinLink: JSON string with LinkedIn URL details.
        annualRevenue: JSON string with amountMicros and currencyCode.
        accountOwnerId: ID of the workspace member who owns this account.
        position: Display sort order.
    """
    params = CreateCompanyParam(
        name=name, domainName=domainName, address=address,
        linkedinLink=linkedinLink, annualRevenue=annualRevenue,
        accountOwnerId=accountOwnerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_company(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_company(
    id: str = "",
    name: str = None,
    domainName: str = None,
    address: str = None,
    linkedinLink: str = None,
    annualRevenue: str = None,
    accountOwnerId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing company record.

    Args:
        id: The unique ID of the company to update (required).
        name: Updated name of the company.
        domainName: Updated domain name as JSON string.
        address: Updated address as JSON string.
        linkedinLink: Updated LinkedIn link as JSON string.
        annualRevenue: Updated annual revenue as JSON string.
        accountOwnerId: Updated account owner workspace member ID.
        position: Updated display sort order.
    """
    params = UpdateCompanyParam(
        id=id, name=name, domainName=domainName, address=address,
        linkedinLink=linkedinLink, annualRevenue=annualRevenue,
        accountOwnerId=accountOwnerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_company(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_companies(
    ids: list[str] = [],
    name: str = None,
    domainName: str = None,
    address: str = None,
    linkedinLink: str = None,
    annualRevenue: str = None,
    accountOwnerId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update company records by IDs.

    Args:
        ids: List of company IDs to update (required).
        name: Updated name for all selected companies.
        domainName: Updated domain name as JSON string.
        address: Updated address as JSON string.
        linkedinLink: Updated LinkedIn link as JSON string.
        annualRevenue: Updated annual revenue as JSON string.
        accountOwnerId: Updated account owner workspace member ID.
        position: Updated display sort order.
    """
    params = UpdateCompanyParam(
        name=name, domainName=domainName, address=address,
        linkedinLink=linkedinLink, annualRevenue=annualRevenue,
        accountOwnerId=accountOwnerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_companies(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_company_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a company by its ID (hard destroy).

    Args:
        id: The unique ID of the company to delete (required).
    """
    await get_client().delete_company_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_companies(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete companies by IDs (hard destroy).

    Args:
        ids: List of company IDs to delete (required).
    """
    await get_client().delete_companies(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Person Tools
# =============================================================================
@mcp.tool()
async def list_people(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all person records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_people(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_person_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single person by their ID.

    Args:
        id: The unique ID of the person (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_person_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_person(
    name: str = "",
    emails: str = "",
    phones: str = "",
    jobTitle: str = "",
    linkedinLink: str = "",
    companyId: str = "",
    avatarUrl: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new person record.

    Args:
        name: JSON string with firstName and lastName.
        emails: JSON string with primaryEmail and additionalEmails.
        phones: JSON string with phone fields.
        jobTitle: Job title of the person.
        linkedinLink: JSON string with LinkedIn URL details.
        companyId: ID of the associated company.
        avatarUrl: URL to the person's avatar image.
        position: Display sort order.
    """
    params = CreatePersonParam(
        name=name, emails=emails, phones=phones, jobTitle=jobTitle,
        linkedinLink=linkedinLink, companyId=companyId, avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_person(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_person(
    id: str = "",
    name: str = None,
    emails: str = None,
    phones: str = None,
    jobTitle: str = None,
    linkedinLink: str = None,
    companyId: str = None,
    avatarUrl: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing person record.

    Args:
        id: The unique ID of the person to update (required).
        name: Updated name as JSON string.
        emails: Updated emails as JSON string.
        phones: Updated phones as JSON string.
        jobTitle: Updated job title.
        linkedinLink: Updated LinkedIn link as JSON string.
        companyId: Updated associated company ID.
        avatarUrl: Updated avatar URL.
        position: Updated display sort order.
    """
    params = UpdatePersonParam(
        id=id, name=name, emails=emails, phones=phones, jobTitle=jobTitle,
        linkedinLink=linkedinLink, companyId=companyId, avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_person(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_people(
    ids: list[str] = [],
    name: str = None,
    emails: str = None,
    phones: str = None,
    jobTitle: str = None,
    linkedinLink: str = None,
    companyId: str = None,
    avatarUrl: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update person records by IDs.

    Args:
        ids: List of person IDs to update (required).
        name: Updated name as JSON string.
        emails: Updated emails as JSON string.
        phones: Updated phones as JSON string.
        jobTitle: Updated job title.
        linkedinLink: Updated LinkedIn link as JSON string.
        companyId: Updated associated company ID.
        avatarUrl: Updated avatar URL.
        position: Updated display sort order.
    """
    params = UpdatePersonParam(
        name=name, emails=emails, phones=phones, jobTitle=jobTitle,
        linkedinLink=linkedinLink, companyId=companyId, avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_people(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_person_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a person by their ID (hard destroy).

    Args:
        id: The unique ID of the person to delete (required).
    """
    await get_client().delete_person_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_people(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete people by IDs (hard destroy).

    Args:
        ids: List of person IDs to delete (required).
    """
    await get_client().delete_people(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Opportunity Tools
# =============================================================================
@mcp.tool()
async def list_opportunities(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all opportunity records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_opportunities(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_opportunity_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single opportunity by its ID.

    Args:
        id: The unique ID of the opportunity (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_opportunity_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_opportunity(
    name: str = "",
    amount: str = "",
    closeDate: str = "",
    stage: str = "",
    companyId: str = "",
    pointOfContactId: str = "",
    ownerId: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new opportunity record.

    Args:
        name: Name of the opportunity (required).
        amount: JSON string with amountMicros and currencyCode.
        closeDate: Expected close date (ISO 8601 with UTC offset).
        stage: Pipeline stage (e.g. NEW, SCREENING, MEETING, PROPOSAL).
        companyId: ID of the associated company.
        pointOfContactId: ID of the associated person.
        ownerId: ID of the workspace member who owns this opportunity.
        position: Display sort order.
    """
    params = CreateOpportunityParam(
        name=name, amount=amount, closeDate=closeDate, stage=stage,
        companyId=companyId, pointOfContactId=pointOfContactId, ownerId=ownerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_opportunity(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_opportunity(
    id: str = "",
    name: str = None,
    amount: str = None,
    closeDate: str = None,
    stage: str = None,
    companyId: str = None,
    pointOfContactId: str = None,
    ownerId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing opportunity record.

    Args:
        id: The unique ID of the opportunity to update (required).
        name: Updated name of the opportunity.
        amount: Updated amount as JSON string.
        closeDate: Updated close date (ISO 8601 with UTC offset).
        stage: Updated pipeline stage.
        companyId: Updated associated company ID.
        pointOfContactId: Updated associated person ID.
        ownerId: Updated owner workspace member ID.
        position: Updated display sort order.
    """
    params = UpdateOpportunityParam(
        id=id, name=name, amount=amount, closeDate=closeDate, stage=stage,
        companyId=companyId, pointOfContactId=pointOfContactId, ownerId=ownerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_opportunity(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_opportunities(
    ids: list[str] = [],
    name: str = None,
    amount: str = None,
    closeDate: str = None,
    stage: str = None,
    companyId: str = None,
    pointOfContactId: str = None,
    ownerId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update opportunity records by IDs.

    Args:
        ids: List of opportunity IDs to update (required).
        name: Updated name of the opportunity.
        amount: Updated amount as JSON string.
        closeDate: Updated close date (ISO 8601 with UTC offset).
        stage: Updated pipeline stage.
        companyId: Updated associated company ID.
        pointOfContactId: Updated associated person ID.
        ownerId: Updated owner workspace member ID.
        position: Updated display sort order.
    """
    params = UpdateOpportunityParam(
        name=name, amount=amount, closeDate=closeDate, stage=stage,
        companyId=companyId, pointOfContactId=pointOfContactId, ownerId=ownerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_opportunities(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_opportunity_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete an opportunity by its ID (hard destroy).

    Args:
        id: The unique ID of the opportunity to delete (required).
    """
    await get_client().delete_opportunity_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_opportunities(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete opportunities by IDs (hard destroy).

    Args:
        ids: List of opportunity IDs to delete (required).
    """
    await get_client().delete_opportunities(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Note Tools
# =============================================================================
@mcp.tool()
async def list_notes(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all note records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_notes(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_note_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single note by its ID.

    Args:
        id: The unique ID of the note (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_note_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_note(
    title: str = "",
    bodyV2: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new note record.

    Args:
        title: Title of the note (required).
        bodyV2: JSON string with blocknote and markdown fields.
        position: Display sort order.
    """
    params = CreateNoteParam(title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().create_note(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_note(
    id: str = "",
    title: str = None,
    bodyV2: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing note record.

    Args:
        id: The unique ID of the note to update (required).
        title: Updated title of the note.
        bodyV2: Updated body as JSON string.
        position: Updated display sort order.
    """
    params = UpdateNoteParam(id=id, title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().update_note(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_notes(
    ids: list[str] = [],
    title: str = None,
    bodyV2: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update note records by IDs.

    Args:
        ids: List of note IDs to update (required).
        title: Updated title of the note.
        bodyV2: Updated body as JSON string.
        position: Updated display sort order.
    """
    params = UpdateNoteParam(title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().update_notes(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_note_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a note by its ID (hard destroy).

    Args:
        id: The unique ID of the note to delete (required).
    """
    await get_client().delete_note_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_notes(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete notes by IDs (hard destroy).

    Args:
        ids: List of note IDs to delete (required).
    """
    await get_client().delete_notes(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Task Tools
# =============================================================================
@mcp.tool()
async def list_tasks(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all task records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_tasks(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_task_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single task by its ID.

    Args:
        id: The unique ID of the task (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_task_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_task(
    title: str = "",
    bodyV2: str = "",
    status: str = "",
    dueAt: str = "",
    assigneeId: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new task record.

    Args:
        title: Title of the task (required).
        bodyV2: JSON string with blocknote and markdown fields.
        status: Task status (e.g. TODO, IN_PROGRESS, DONE).
        dueAt: Due date (ISO 8601 with UTC offset).
        assigneeId: ID of the workspace member assigned to this task.
        position: Display sort order.
    """
    params = CreateTaskParam(
        title=title, bodyV2=bodyV2, status=status, dueAt=dueAt,
        assigneeId=assigneeId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_task(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_task(
    id: str = "",
    title: str = None,
    bodyV2: str = None,
    status: str = None,
    dueAt: str = None,
    assigneeId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing task record.

    Args:
        id: The unique ID of the task to update (required).
        title: Updated title of the task.
        bodyV2: Updated body as JSON string.
        status: Updated task status.
        dueAt: Updated due date (ISO 8601 with UTC offset).
        assigneeId: Updated assignee workspace member ID.
        position: Updated display sort order.
    """
    params = UpdateTaskParam(
        id=id, title=title, bodyV2=bodyV2, status=status, dueAt=dueAt,
        assigneeId=assigneeId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_task(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_tasks(
    ids: list[str] = [],
    title: str = None,
    bodyV2: str = None,
    status: str = None,
    dueAt: str = None,
    assigneeId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update task records by IDs.

    Args:
        ids: List of task IDs to update (required).
        title: Updated title of the task.
        bodyV2: Updated body as JSON string.
        status: Updated task status.
        dueAt: Updated due date (ISO 8601 with UTC offset).
        assigneeId: Updated assignee workspace member ID.
        position: Updated display sort order.
    """
    params = UpdateTaskParam(
        title=title, bodyV2=bodyV2, status=status, dueAt=dueAt,
        assigneeId=assigneeId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_tasks(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_task_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a task by its ID (hard destroy).

    Args:
        id: The unique ID of the task to delete (required).
    """
    await get_client().delete_task_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_tasks(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete tasks by IDs (hard destroy).

    Args:
        ids: List of task IDs to delete (required).
    """
    await get_client().delete_tasks(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Workflow Tools
# =============================================================================
@mcp.tool()
async def list_workflows(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all workflow records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workflows(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_workflow_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single workflow by its ID.

    Args:
        id: The unique ID of the workflow (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_workflow_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_workflow(
    name: str = "",
    statuses: str = "[]",
    lastPublishedVersionId: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new workflow record.

    Args:
        name: Name of the workflow (required).
        statuses: JSON array of workflow statuses (e.g. ["ACTIVE"]).
        lastPublishedVersionId: ID of the last published version.
        position: Display sort order.
    """
    params = CreateWorkflowParam(
        name=name, statuses=statuses, lastPublishedVersionId=lastPublishedVersionId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_workflow(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_workflow(
    id: str = "",
    name: str = None,
    statuses: str = None,
    lastPublishedVersionId: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing workflow record.

    Args:
        id: The unique ID of the workflow to update (required).
        name: Updated name of the workflow.
        statuses: Updated statuses as JSON array string.
        lastPublishedVersionId: Updated last published version ID.
        position: Updated display sort order.
    """
    params = UpdateWorkflowParam(
        id=id, name=name, statuses=statuses, lastPublishedVersionId=lastPublishedVersionId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workflow(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
@mcp.tool()
async def delete_workflow_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a workflow by its ID (hard destroy).

    Args:
        id: The unique ID of the workflow to delete (required).
    """
    await get_client().delete_workflow_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


# =============================================================================
# WorkspaceMember Tools
# =============================================================================
@mcp.tool()
async def list_workspace_members(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all workspace member records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workspace_members(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_workspace_member_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single workspace member by their ID.

    Args:
        id: The unique ID of the workspace member (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_workspace_member_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def update_workspace_member(
    id: str = "",
    name: str = None,
    colorScheme: str = None,
    locale: str = None,
    avatarUrl: str = None,
    userEmail: str = None,
    calendarStartDay: int = None,
    timeZone: str = None,
    dateFormat: str = None,
    timeFormat: str = None,
    numberFormat: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing workspace member record.

    Args:
        id: The unique ID of the workspace member to update (required).
        name: Updated name as JSON string.
        colorScheme: Updated UI color scheme.
        locale: Updated locale code.
        avatarUrl: Updated avatar URL.
        userEmail: Updated user email address.
        calendarStartDay: Updated first day of the week.
        timeZone: Updated timezone string.
        dateFormat: Updated date format preference.
        timeFormat: Updated time format preference.
        numberFormat: Updated number format preference.
        position: Updated display sort order.
    """
    params = UpdateWorkspaceMemberParam(
        id=id, name=name, colorScheme=colorScheme, locale=locale, avatarUrl=avatarUrl,
        userEmail=userEmail, calendarStartDay=calendarStartDay, timeZone=timeZone,
        dateFormat=dateFormat, timeFormat=timeFormat, numberFormat=numberFormat, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workspace_member(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_workspace_members(
    ids: list[str] = [],
    name: str = None,
    colorScheme: str = None,
    locale: str = None,
    avatarUrl: str = None,
    userEmail: str = None,
    calendarStartDay: int = None,
    timeZone: str = None,
    dateFormat: str = None,
    timeFormat: str = None,
    numberFormat: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update workspace member records by IDs.

    Args:
        ids: List of workspace member IDs to update (required).
        name: Updated name as JSON string.
        colorScheme: Updated UI color scheme.
        locale: Updated locale code.
        avatarUrl: Updated avatar URL.
        userEmail: Updated user email address.
        calendarStartDay: Updated first day of the week.
        timeZone: Updated timezone string.
        dateFormat: Updated date format preference.
        timeFormat: Updated time format preference.
        numberFormat: Updated number format preference.
        position: Updated display sort order.
    """
    params = UpdateWorkspaceMemberParam(
        name=name, colorScheme=colorScheme, locale=locale, avatarUrl=avatarUrl,
        userEmail=userEmail, calendarStartDay=calendarStartDay, timeZone=timeZone,
        dateFormat=dateFormat, timeFormat=timeFormat, numberFormat=numberFormat, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workspace_members(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_workspace_member_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a workspace member by their ID (hard destroy).

    Args:
        id: The unique ID of the workspace member to delete (required).
    """
    await get_client().delete_workspace_member_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_workspace_members(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete workspace members by IDs (hard destroy).

    Args:
        ids: List of workspace member IDs to delete (required).
    """
    await get_client().delete_workspace_members(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Attachment Tools
# =============================================================================
@mcp.tool()
async def list_attachments(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all attachment records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_attachments(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_attachment_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single attachment by its ID.

    Args:
        id: The unique ID of the attachment (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_attachment_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_attachment(
    name: str = "",
    fullPath: str = "",
    fileCategory: str = "",
    authorId: str = "",
    targetTaskId: str = "",
    targetNoteId: str = "",
    targetPersonId: str = "",
    targetCompanyId: str = "",
    targetOpportunityId: str = "",
    targetDashboardId: str = "",
    targetWorkflowId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new attachment record.

    Args:
        name: Name of the attachment file.
        fullPath: Full file path.
        fileCategory: Category of the file.
        authorId: ID of the workspace member who authored this attachment.
        targetTaskId: ID of the associated task.
        targetNoteId: ID of the associated note.
        targetPersonId: ID of the associated person.
        targetCompanyId: ID of the associated company.
        targetOpportunityId: ID of the associated opportunity.
        targetDashboardId: ID of the associated dashboard.
        targetWorkflowId: ID of the associated workflow.
    """
    params = CreateAttachmentParam(
        name=name, fullPath=fullPath, fileCategory=fileCategory,
        authorId=authorId, targetTaskId=targetTaskId, targetNoteId=targetNoteId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetDashboardId=targetDashboardId,
        targetWorkflowId=targetWorkflowId,
    )
    payload = _build_payload(params)
    return await get_client().create_attachment(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_attachment(
    id: str = "",
    name: str = None,
    fullPath: str = None,
    type: str = None,
    fileCategory: str = None,
    authorId: str = None,
    targetTaskId: str = None,
    targetNoteId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    targetDashboardId: str = None,
    targetWorkflowId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing attachment record.

    Args:
        id: The unique ID of the attachment to update (required).
        name: Updated name of the attachment file.
        fullPath: Updated full file path.
        type: Updated MIME type of the file.
        fileCategory: Updated category of the file.
        authorId: Updated author workspace member ID.
        targetTaskId: Updated associated task ID.
        targetNoteId: Updated associated note ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
        targetDashboardId: Updated associated dashboard ID.
        targetWorkflowId: Updated associated workflow ID.
    """
    params = UpdateAttachmentParam(
        id=id, name=name, fullPath=fullPath, type=type, fileCategory=fileCategory,
        authorId=authorId, targetTaskId=targetTaskId, targetNoteId=targetNoteId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetDashboardId=targetDashboardId,
        targetWorkflowId=targetWorkflowId,
    )
    payload = _build_payload(params)
    return await get_client().update_attachment(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_attachments(
    ids: list[str] = [],
    name: str = None,
    fullPath: str = None,
    type: str = None,
    fileCategory: str = None,
    authorId: str = None,
    targetTaskId: str = None,
    targetNoteId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    targetDashboardId: str = None,
    targetWorkflowId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update attachment records by IDs.

    Args:
        ids: List of attachment IDs to update (required).
        name: Updated name of the attachment file.
        fullPath: Updated full file path.
        type: Updated MIME type of the file.
        fileCategory: Updated category of the file.
        authorId: Updated author workspace member ID.
        targetTaskId: Updated associated task ID.
        targetNoteId: Updated associated note ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
        targetDashboardId: Updated associated dashboard ID.
        targetWorkflowId: Updated associated workflow ID.
    """
    params = UpdateAttachmentParam(
        name=name, fullPath=fullPath, type=type, fileCategory=fileCategory,
        authorId=authorId, targetTaskId=targetTaskId, targetNoteId=targetNoteId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetDashboardId=targetDashboardId,
        targetWorkflowId=targetWorkflowId,
    )
    payload = _build_payload(params)
    return await get_client().update_attachments(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_attachment_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete an attachment by its ID (hard destroy).

    Args:
        id: The unique ID of the attachment to delete (required).
    """
    await get_client().delete_attachment_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_attachments(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete attachments by IDs (hard destroy).

    Args:
        ids: List of attachment IDs to delete (required).
    """
    await get_client().delete_attachments(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# NoteTarget Tools
# =============================================================================
@mcp.tool()
async def list_note_targets(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all note target records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_note_targets(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_note_target_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single note target by its ID.

    Args:
        id: The unique ID of the note target (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_note_target_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_note_target(
    noteId: str = "",
    targetPersonId: str = "",
    targetCompanyId: str = "",
    targetOpportunityId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new note target record.

    Args:
        noteId: ID of the associated note.
        targetPersonId: ID of the associated person.
        targetCompanyId: ID of the associated company.
        targetOpportunityId: ID of the associated opportunity.
    """
    params = CreateNoteTargetParam(
        noteId=noteId, targetPersonId=targetPersonId,
        targetCompanyId=targetCompanyId, targetOpportunityId=targetOpportunityId,
    )
    payload = _build_payload(params)
    return await get_client().create_note_target(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_note_target(
    id: str = "",
    noteId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing note target record.

    Args:
        id: The unique ID of the note target to update (required).
        noteId: Updated associated note ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
    """
    params = UpdateNoteTargetParam(
        id=id, noteId=noteId, targetPersonId=targetPersonId,
        targetCompanyId=targetCompanyId, targetOpportunityId=targetOpportunityId,
    )
    payload = _build_payload(params)
    return await get_client().update_note_target(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_note_targets(
    ids: list[str] = [],
    noteId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update note target records by IDs.

    Args:
        ids: List of note target IDs to update (required).
        noteId: Updated associated note ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
    """
    params = UpdateNoteTargetParam(
        noteId=noteId, targetPersonId=targetPersonId,
        targetCompanyId=targetCompanyId, targetOpportunityId=targetOpportunityId,
    )
    payload = _build_payload(params)
    return await get_client().update_note_targets(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_note_target_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a note target by its ID (hard destroy).

    Args:
        id: The unique ID of the note target to delete (required).
    """
    await get_client().delete_note_target_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_note_targets(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete note targets by IDs (hard destroy).

    Args:
        ids: List of note target IDs to delete (required).
    """
    await get_client().delete_note_targets(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# TaskTarget Tools
# =============================================================================
@mcp.tool()
async def list_task_targets(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all task target records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_task_targets(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_task_target_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single task target by its ID.

    Args:
        id: The unique ID of the task target (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_task_target_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_task_target(
    taskId: str = "",
    targetPersonId: str = "",
    targetCompanyId: str = "",
    targetOpportunityId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new task target record.

    Args:
        taskId: ID of the associated task.
        targetPersonId: ID of the associated person.
        targetCompanyId: ID of the associated company.
        targetOpportunityId: ID of the associated opportunity.
    """
    params = CreateTaskTargetParam(
        taskId=taskId, targetPersonId=targetPersonId,
        targetCompanyId=targetCompanyId, targetOpportunityId=targetOpportunityId,
    )
    payload = _build_payload(params)
    return await get_client().create_task_target(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_task_target(
    id: str = "",
    taskId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing task target record.

    Args:
        id: The unique ID of the task target to update (required).
        taskId: Updated associated task ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
    """
    params = UpdateTaskTargetParam(
        id=id, taskId=taskId, targetPersonId=targetPersonId,
        targetCompanyId=targetCompanyId, targetOpportunityId=targetOpportunityId,
    )
    payload = _build_payload(params)
    return await get_client().update_task_target(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_task_targets(
    ids: list[str] = [],
    taskId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update task target records by IDs.

    Args:
        ids: List of task target IDs to update (required).
        taskId: Updated associated task ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
    """
    params = UpdateTaskTargetParam(
        taskId=taskId, targetPersonId=targetPersonId,
        targetCompanyId=targetCompanyId, targetOpportunityId=targetOpportunityId,
    )
    payload = _build_payload(params)
    return await get_client().update_task_targets(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_task_target_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a task target by its ID (hard destroy).

    Args:
        id: The unique ID of the task target to delete (required).
    """
    await get_client().delete_task_target_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_task_targets(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete task targets by IDs (hard destroy).

    Args:
        ids: List of task target IDs to delete (required).
    """
    await get_client().delete_task_targets(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# TimelineActivity Tools
# =============================================================================
@mcp.tool()
async def list_timeline_activities(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all timeline activity records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_timeline_activities(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_timeline_activity_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single timeline activity by its ID.

    Args:
        id: The unique ID of the timeline activity (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_timeline_activity_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_timeline_activity(
    name: str = "",
    happensAt: str = "",
    workspaceMemberId: str = "",
    linkedRecordId: str = "",
    linkedObjectMetadataId: str = "",
    targetPersonId: str = "",
    targetCompanyId: str = "",
    targetOpportunityId: str = "",
    targetNoteId: str = "",
    targetTaskId: str = "",
    targetWorkflowId: str = "",
    targetWorkflowVersionId: str = "",
    targetWorkflowRunId: str = "",
    targetDashboardId: str = "",
    targetMessageListId: str = "",
    targetMessageCampaignId: str = "",
    properties: str = "{}",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new timeline activity record.

    Args:
        name: Name of the activity (required).
        happensAt: When the activity occurred (ISO 8601 with UTC offset).
        workspaceMemberId: ID of the associated workspace member.
        linkedRecordId: ID of the linked record.
        linkedObjectMetadataId: Metadata ID of the linked object.
        targetPersonId: ID of the associated person.
        targetCompanyId: ID of the associated company.
        targetOpportunityId: ID of the associated opportunity.
        targetNoteId: ID of the associated note.
        targetTaskId: ID of the associated task.
        targetWorkflowId: ID of the associated workflow.
        targetWorkflowVersionId: ID of the associated workflow version.
        targetWorkflowRunId: ID of the associated workflow run.
        targetDashboardId: ID of the associated dashboard.
        targetMessageListId: ID of the associated message list.
        targetMessageCampaignId: ID of the associated message campaign.
        properties: JSON string with additional properties.
        position: Display sort order.
    """
    params = CreateTimelineActivityParam(
        name=name, happensAt=happensAt, workspaceMemberId=workspaceMemberId,
        linkedRecordId=linkedRecordId, linkedObjectMetadataId=linkedObjectMetadataId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetNoteId=targetNoteId,
        targetTaskId=targetTaskId, targetWorkflowId=targetWorkflowId,
        targetWorkflowVersionId=targetWorkflowVersionId, targetWorkflowRunId=targetWorkflowRunId,
        targetDashboardId=targetDashboardId, targetMessageListId=targetMessageListId,
        targetMessageCampaignId=targetMessageCampaignId, properties=properties, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_timeline_activity(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_timeline_activity(
    id: str = "",
    name: str = None,
    happensAt: str = None,
    workspaceMemberId: str = None,
    linkedRecordId: str = None,
    linkedObjectMetadataId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    targetNoteId: str = None,
    targetTaskId: str = None,
    targetWorkflowId: str = None,
    targetWorkflowVersionId: str = None,
    targetWorkflowRunId: str = None,
    targetDashboardId: str = None,
    targetMessageListId: str = None,
    targetMessageCampaignId: str = None,
    properties: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing timeline activity record.

    Args:
        id: The unique ID of the timeline activity to update (required).
        name: Updated name of the activity.
        happensAt: Updated occurrence time (ISO 8601 with UTC offset).
        workspaceMemberId: Updated associated workspace member ID.
        linkedRecordId: Updated linked record ID.
        linkedObjectMetadataId: Updated metadata ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
        targetNoteId: Updated associated note ID.
        targetTaskId: Updated associated task ID.
        targetWorkflowId: Updated associated workflow ID.
        targetWorkflowVersionId: Updated associated workflow version ID.
        targetWorkflowRunId: Updated associated workflow run ID.
        targetDashboardId: Updated associated dashboard ID.
        targetMessageListId: Updated associated message list ID.
        targetMessageCampaignId: Updated associated message campaign ID.
        properties: Updated properties as JSON string.
        position: Updated display sort order.
    """
    params = UpdateTimelineActivityParam(
        id=id, name=name, happensAt=happensAt, workspaceMemberId=workspaceMemberId,
        linkedRecordId=linkedRecordId, linkedObjectMetadataId=linkedObjectMetadataId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetNoteId=targetNoteId,
        targetTaskId=targetTaskId, targetWorkflowId=targetWorkflowId,
        targetWorkflowVersionId=targetWorkflowVersionId, targetWorkflowRunId=targetWorkflowRunId,
        targetDashboardId=targetDashboardId, targetMessageListId=targetMessageListId,
        targetMessageCampaignId=targetMessageCampaignId, properties=properties, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_timeline_activity(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_timeline_activities(
    ids: list[str] = [],
    name: str = None,
    happensAt: str = None,
    workspaceMemberId: str = None,
    linkedRecordId: str = None,
    linkedObjectMetadataId: str = None,
    targetPersonId: str = None,
    targetCompanyId: str = None,
    targetOpportunityId: str = None,
    targetNoteId: str = None,
    targetTaskId: str = None,
    targetWorkflowId: str = None,
    targetWorkflowVersionId: str = None,
    targetWorkflowRunId: str = None,
    targetDashboardId: str = None,
    targetMessageListId: str = None,
    targetMessageCampaignId: str = None,
    properties: str = None,
    position: int = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update timeline activity records by IDs.

    Args:
        ids: List of timeline activity IDs to update (required).
        name: Updated name of the activity.
        happensAt: Updated occurrence time (ISO 8601 with UTC offset).
        workspaceMemberId: Updated associated workspace member ID.
        linkedRecordId: Updated linked record ID.
        linkedObjectMetadataId: Updated metadata ID.
        targetPersonId: Updated associated person ID.
        targetCompanyId: Updated associated company ID.
        targetOpportunityId: Updated associated opportunity ID.
        targetNoteId: Updated associated note ID.
        targetTaskId: Updated associated task ID.
        targetWorkflowId: Updated associated workflow ID.
        targetWorkflowVersionId: Updated associated workflow version ID.
        targetWorkflowRunId: Updated associated workflow run ID.
        targetDashboardId: Updated associated dashboard ID.
        targetMessageListId: Updated associated message list ID.
        targetMessageCampaignId: Updated associated message campaign ID.
        properties: Updated properties as JSON string.
        position: Updated display sort order.
    """
    params = UpdateTimelineActivityParam(
        name=name, happensAt=happensAt, workspaceMemberId=workspaceMemberId,
        linkedRecordId=linkedRecordId, linkedObjectMetadataId=linkedObjectMetadataId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetNoteId=targetNoteId,
        targetTaskId=targetTaskId, targetWorkflowId=targetWorkflowId,
        targetWorkflowVersionId=targetWorkflowVersionId, targetWorkflowRunId=targetWorkflowRunId,
        targetDashboardId=targetDashboardId, targetMessageListId=targetMessageListId,
        targetMessageCampaignId=targetMessageCampaignId, properties=properties, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_timeline_activities(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_timeline_activity_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a timeline activity by its ID (hard destroy).

    Args:
        id: The unique ID of the timeline activity to delete (required).
    """
    await get_client().delete_timeline_activity_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_timeline_activities(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete timeline activities by IDs (hard destroy).

    Args:
        ids: List of timeline activity IDs to delete (required).
    """
    await get_client().delete_timeline_activities(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# CalendarEvent Tools
# =============================================================================
@mcp.tool()
async def list_calendar_events(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all calendar event records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_calendar_events(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_calendar_event_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single calendar event by its ID.

    Args:
        id: The unique ID of the calendar event (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_calendar_event_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_calendar_event(
    title: str = "",
    isCanceled: bool = False,
    isFullDay: bool = False,
    startsAt: str = "",
    endsAt: str = "",
    description: str = "",
    location: str = "",
    iCalUid: str = "",
    conferenceSolution: str = "",
    conferenceLink: str = "{}",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new calendar event record.

    Args:
        title: Title of the calendar event.
        isCanceled: Whether the event is canceled.
        isFullDay: Whether the event is an all-day event.
        startsAt: Start time (ISO 8601 with UTC offset).
        endsAt: End time (ISO 8601 with UTC offset).
        description: Description of the event.
        location: Location of the event.
        iCalUid: iCal UID for the event.
        conferenceSolution: Conference solution type.
        conferenceLink: JSON string with conference link details.
    """
    params = CreateCalendarEventParam(
        title=title, isCanceled=isCanceled, isFullDay=isFullDay,
        startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, iCalUid=iCalUid, conferenceSolution=conferenceSolution,
        conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().create_calendar_event(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_calendar_event(
    id: str = "",
    title: str = None,
    isCanceled: bool = None,
    isFullDay: bool = None,
    startsAt: str = None,
    endsAt: str = None,
    description: str = None,
    location: str = None,
    iCalUid: str = None,
    conferenceSolution: str = None,
    conferenceLink: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing calendar event record.

    Args:
        id: The unique ID of the calendar event to update (required).
        title: Updated title of the calendar event.
        isCanceled: Updated cancellation status.
        isFullDay: Updated all-day flag.
        startsAt: Updated start time (ISO 8601 with UTC offset).
        endsAt: Updated end time (ISO 8601 with UTC offset).
        description: Updated description.
        location: Updated location.
        iCalUid: Updated iCal UID.
        conferenceSolution: Updated conference solution type.
        conferenceLink: Updated conference link as JSON string.
    """
    params = UpdateCalendarEventParam(
        id=id, title=title, isCanceled=isCanceled, isFullDay=isFullDay,
        startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, iCalUid=iCalUid, conferenceSolution=conferenceSolution,
        conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_event(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_calendar_events(
    ids: list[str] = [],
    title: str = None,
    isCanceled: bool = None,
    isFullDay: bool = None,
    startsAt: str = None,
    endsAt: str = None,
    description: str = None,
    location: str = None,
    iCalUid: str = None,
    conferenceSolution: str = None,
    conferenceLink: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update calendar event records by IDs.

    Args:
        ids: List of calendar event IDs to update (required).
        title: Updated title of the calendar event.
        isCanceled: Updated cancellation status.
        isFullDay: Updated all-day flag.
        startsAt: Updated start time (ISO 8601 with UTC offset).
        endsAt: Updated end time (ISO 8601 with UTC offset).
        description: Updated description.
        location: Updated location.
        iCalUid: Updated iCal UID.
        conferenceSolution: Updated conference solution type.
        conferenceLink: Updated conference link as JSON string.
    """
    params = UpdateCalendarEventParam(
        title=title, isCanceled=isCanceled, isFullDay=isFullDay,
        startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, iCalUid=iCalUid, conferenceSolution=conferenceSolution,
        conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_events(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_calendar_event_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a calendar event by its ID (hard destroy).

    Args:
        id: The unique ID of the calendar event to delete (required).
    """
    await get_client().delete_calendar_event_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_calendar_events(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete calendar events by IDs (hard destroy).

    Args:
        ids: List of calendar event IDs to delete (required).
    """
    await get_client().delete_calendar_events(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# CalendarEventParticipant Tools
# =============================================================================
@mcp.tool()
async def list_calendar_event_participants(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all calendar event participant records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_calendar_event_participants(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_calendar_event_participant_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single calendar event participant by its ID.

    Args:
        id: The unique ID of the calendar event participant (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_calendar_event_participant_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_calendar_event_participant(
    calendarEventId: str = "",
    handle: str = "",
    displayName: str = "",
    isOrganizer: bool = False,
    responseStatus: str = "NEEDS_ACTION",
    personId: str = "",
    workspaceMemberId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new calendar event participant record.

    Args:
        calendarEventId: ID of the associated calendar event (required).
        handle: Email handle of the participant.
        displayName: Display name of the participant.
        isOrganizer: Whether this participant is the organizer.
        responseStatus: Response status (NEEDS_ACTION, DECLINED, TENTATIVE, ACCEPTED).
        personId: ID of the associated person.
        workspaceMemberId: ID of the associated workspace member.
    """
    params = CreateCalendarEventParticipantParam(
        calendarEventId=calendarEventId, handle=handle, displayName=displayName,
        isOrganizer=isOrganizer, responseStatus=responseStatus,
        personId=personId, workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().create_calendar_event_participant(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_calendar_event_participant(
    id: str = "",
    calendarEventId: str = None,
    handle: str = None,
    displayName: str = None,
    isOrganizer: bool = None,
    responseStatus: str = None,
    personId: str = None,
    workspaceMemberId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing calendar event participant record.

    Args:
        id: The unique ID of the calendar event participant to update (required).
        calendarEventId: Updated associated calendar event ID.
        handle: Updated email handle.
        displayName: Updated display name.
        isOrganizer: Updated organizer flag.
        responseStatus: Updated response status.
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
    """
    params = UpdateCalendarEventParticipantParam(
        id=id, calendarEventId=calendarEventId, handle=handle, displayName=displayName,
        isOrganizer=isOrganizer, responseStatus=responseStatus,
        personId=personId, workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_event_participant(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_calendar_event_participants(
    ids: list[str] = [],
    calendarEventId: str = None,
    handle: str = None,
    displayName: str = None,
    isOrganizer: bool = None,
    responseStatus: str = None,
    personId: str = None,
    workspaceMemberId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update calendar event participant records by IDs.

    Args:
        ids: List of calendar event participant IDs to update (required).
        calendarEventId: Updated associated calendar event ID.
        handle: Updated email handle.
        displayName: Updated display name.
        isOrganizer: Updated organizer flag.
        responseStatus: Updated response status.
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
    """
    params = UpdateCalendarEventParticipantParam(
        calendarEventId=calendarEventId, handle=handle, displayName=displayName,
        isOrganizer=isOrganizer, responseStatus=responseStatus,
        personId=personId, workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_event_participants(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_calendar_event_participant_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a calendar event participant by its ID (hard destroy).

    Args:
        id: The unique ID of the calendar event participant to delete (required).
    """
    await get_client().delete_calendar_event_participant_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_calendar_event_participants(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete calendar event participants by IDs (hard destroy).

    Args:
        ids: List of calendar event participant IDs to delete (required).
    """
    await get_client().delete_calendar_event_participants(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Message Tools
# =============================================================================
@mcp.tool()
async def list_messages(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all message records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messages(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_message_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single message by its ID.

    Args:
        id: The unique ID of the message (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_message_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_message(
    headerMessageId: str = "",
    subject: str = "",
    text: str = "",
    receivedAt: str = "",
    messageThreadId: str = "",
    messageCampaignId: str = "",
    deliveryStatus: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message record.

    Args:
        headerMessageId: Header message ID.
        subject: Subject of the message.
        text: Body text of the message.
        receivedAt: Received timestamp (ISO 8601 with UTC offset).
        messageThreadId: ID of the associated message thread.
        messageCampaignId: ID of the associated message campaign.
        deliveryStatus: Delivery status of the message.
    """
    params = CreateMessageParam(
        headerMessageId=headerMessageId, subject=subject, text=text,
        receivedAt=receivedAt, messageThreadId=messageThreadId,
        messageCampaignId=messageCampaignId, deliveryStatus=deliveryStatus,
    )
    payload = _build_payload(params)
    return await get_client().create_message(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message(
    id: str = "",
    headerMessageId: str = None,
    subject: str = None,
    text: str = None,
    receivedAt: str = None,
    messageThreadId: str = None,
    messageCampaignId: str = None,
    deliveryStatus: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message record.

    Args:
        id: The unique ID of the message to update (required).
        headerMessageId: Updated header message ID.
        subject: Updated subject of the message.
        text: Updated body text of the message.
        receivedAt: Updated received timestamp (ISO 8601 with UTC offset).
        messageThreadId: Updated associated message thread ID.
        messageCampaignId: Updated associated message campaign ID.
        deliveryStatus: Updated delivery status.
    """
    params = UpdateMessageParam(
        id=id, headerMessageId=headerMessageId, subject=subject, text=text,
        receivedAt=receivedAt, messageThreadId=messageThreadId,
        messageCampaignId=messageCampaignId, deliveryStatus=deliveryStatus,
    )
    payload = _build_payload(params)
    return await get_client().update_message(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_messages(
    ids: list[str] = [],
    headerMessageId: str = None,
    subject: str = None,
    text: str = None,
    receivedAt: str = None,
    messageThreadId: str = None,
    messageCampaignId: str = None,
    deliveryStatus: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message records by IDs.

    Args:
        ids: List of message IDs to update (required).
        headerMessageId: Updated header message ID.
        subject: Updated subject of the message.
        text: Updated body text of the message.
        receivedAt: Updated received timestamp (ISO 8601 with UTC offset).
        messageThreadId: Updated associated message thread ID.
        messageCampaignId: Updated associated message campaign ID.
        deliveryStatus: Updated delivery status.
    """
    params = UpdateMessageParam(
        headerMessageId=headerMessageId, subject=subject, text=text,
        receivedAt=receivedAt, messageThreadId=messageThreadId,
        messageCampaignId=messageCampaignId, deliveryStatus=deliveryStatus,
    )
    payload = _build_payload(params)
    return await get_client().update_messages(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_message_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a message by its ID (hard destroy).

    Args:
        id: The unique ID of the message to delete (required).
    """
    await get_client().delete_message_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_messages(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete messages by IDs (hard destroy).

    Args:
        ids: List of message IDs to delete (required).
    """
    await get_client().delete_messages(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# MessageThread Tools
# =============================================================================
@mcp.tool()
async def list_message_threads(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all message thread records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_message_threads(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_message_thread_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single message thread by its ID.

    Args:
        id: The unique ID of the message thread (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_message_thread_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_message_thread(
    subject: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message thread record.

    Args:
        subject: Subject of the message thread.
    """
    params = CreateMessageThreadParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().create_message_thread(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message_thread(
    id: str = "",
    subject: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message thread record.

    Args:
        id: The unique ID of the message thread to update (required).
        subject: Updated subject of the message thread.
    """
    params = UpdateMessageThreadParam(id=id, subject=subject)
    payload = _build_payload(params)
    return await get_client().update_message_thread(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message_threads(
    ids: list[str] = [],
    subject: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message thread records by IDs.

    Args:
        ids: List of message thread IDs to update (required).
        subject: Updated subject of the message thread.
    """
    params = UpdateMessageThreadParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().update_message_threads(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_message_thread_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a message thread by its ID (hard destroy).

    Args:
        id: The unique ID of the message thread to delete (required).
    """
    await get_client().delete_message_thread_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_message_threads(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete message threads by IDs (hard destroy).

    Args:
        ids: List of message thread IDs to delete (required).
    """
    await get_client().delete_message_threads(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# MessageParticipant Tools
# =============================================================================
@mcp.tool()
async def list_message_participants(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all message participant records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_message_participants(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_message_participant_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single message participant by its ID.

    Args:
        id: The unique ID of the message participant (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_message_participant_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_message_participant(
    messageId: str = "",
    role: str = "",
    handle: str = "",
    displayName: str = "",
    personId: str = "",
    workspaceMemberId: str = "",
    messageCampaignId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message participant record.

    Args:
        messageId: ID of the associated message (required).
        role: Role of the participant.
        handle: Email handle of the participant.
        displayName: Display name of the participant.
        personId: ID of the associated person.
        workspaceMemberId: ID of the associated workspace member.
        messageCampaignId: ID of the associated message campaign.
    """
    params = CreateMessageParticipantParam(
        messageId=messageId, role=role, handle=handle, displayName=displayName,
        personId=personId, workspaceMemberId=workspaceMemberId,
        messageCampaignId=messageCampaignId,
    )
    payload = _build_payload(params)
    return await get_client().create_message_participant(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message_participant(
    id: str = "",
    messageId: str = None,
    role: str = None,
    handle: str = None,
    displayName: str = None,
    personId: str = None,
    workspaceMemberId: str = None,
    messageCampaignId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message participant record.

    Args:
        id: The unique ID of the message participant to update (required).
        messageId: Updated associated message ID.
        role: Updated role of the participant.
        handle: Updated email handle.
        displayName: Updated display name.
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
        messageCampaignId: Updated associated message campaign ID.
    """
    params = UpdateMessageParticipantParam(
        id=id, messageId=messageId, role=role, handle=handle, displayName=displayName,
        personId=personId, workspaceMemberId=workspaceMemberId,
        messageCampaignId=messageCampaignId,
    )
    payload = _build_payload(params)
    return await get_client().update_message_participant(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message_participants(
    ids: list[str] = [],
    messageId: str = None,
    role: str = None,
    handle: str = None,
    displayName: str = None,
    personId: str = None,
    workspaceMemberId: str = None,
    messageCampaignId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message participant records by IDs.

    Args:
        ids: List of message participant IDs to update (required).
        messageId: Updated associated message ID.
        role: Updated role of the participant.
        handle: Updated email handle.
        displayName: Updated display name.
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
        messageCampaignId: Updated associated message campaign ID.
    """
    params = UpdateMessageParticipantParam(
        messageId=messageId, role=role, handle=handle, displayName=displayName,
        personId=personId, workspaceMemberId=workspaceMemberId,
        messageCampaignId=messageCampaignId,
    )
    payload = _build_payload(params)
    return await get_client().update_message_participants(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_message_participant_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a message participant by its ID (hard destroy).

    Args:
        id: The unique ID of the message participant to delete (required).
    """
    await get_client().delete_message_participant_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_message_participants(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete message participants by IDs (hard destroy).

    Args:
        ids: List of message participant IDs to delete (required).
    """
    await get_client().delete_message_participants(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# CallRecording Tools
# =============================================================================
@mcp.tool()
async def list_call_recordings(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all call recording records.

    Args:
        include_all_fields: When False (default), each item contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_call_recordings(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool()
async def get_call_recording_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single call recording by its ID.

    Args:
        id: The unique ID of the call recording (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_call_recording_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool()
async def create_call_recording(
    title: str = "",
    status: str = "",
    recordingRequestStatus: str = "",
    applicationId: str = "",
    externalBotId: str = "",
    externalRecordingId: str = "",
    startedAt: str = "",
    endedAt: str = "",
    calendarEventId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new call recording record.

    Args:
        title: Title of the call recording (required).
        status: Status of the call recording.
        recordingRequestStatus: Request status for the recording.
        applicationId: Application ID.
        externalBotId: External bot ID.
        externalRecordingId: External recording ID.
        startedAt: Start time (ISO 8601 with UTC offset).
        endedAt: End time (ISO 8601 with UTC offset).
        calendarEventId: ID of the associated calendar event.
    """
    params = CreateCallRecordingParam(
        title=title, status=status, recordingRequestStatus=recordingRequestStatus,
        applicationId=applicationId, externalBotId=externalBotId,
        externalRecordingId=externalRecordingId, startedAt=startedAt,
        endedAt=endedAt, calendarEventId=calendarEventId,
    )
    payload = _build_payload(params)
    return await get_client().create_call_recording(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_call_recording(
    id: str = "",
    title: str = None,
    status: str = None,
    recordingRequestStatus: str = None,
    applicationId: str = None,
    externalBotId: str = None,
    externalRecordingId: str = None,
    startedAt: str = None,
    endedAt: str = None,
    calendarEventId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing call recording record.

    Args:
        id: The unique ID of the call recording to update (required).
        title: Updated title of the call recording.
        status: Updated status of the call recording.
        recordingRequestStatus: Updated request status.
        applicationId: Updated application ID.
        externalBotId: Updated external bot ID.
        externalRecordingId: Updated external recording ID.
        startedAt: Updated start time (ISO 8601 with UTC offset).
        endedAt: Updated end time (ISO 8601 with UTC offset).
        calendarEventId: Updated associated calendar event ID.
    """
    params = UpdateCallRecordingParam(
        id=id, title=title, status=status, recordingRequestStatus=recordingRequestStatus,
        applicationId=applicationId, externalBotId=externalBotId,
        externalRecordingId=externalRecordingId, startedAt=startedAt,
        endedAt=endedAt, calendarEventId=calendarEventId,
    )
    payload = _build_payload(params)
    return await get_client().update_call_recording(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_call_recordings(
    ids: list[str] = [],
    title: str = None,
    status: str = None,
    recordingRequestStatus: str = None,
    applicationId: str = None,
    externalBotId: str = None,
    externalRecordingId: str = None,
    startedAt: str = None,
    endedAt: str = None,
    calendarEventId: str = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update call recording records by IDs.

    Args:
        ids: List of call recording IDs to update (required).
        title: Updated title of the call recording.
        status: Updated status of the call recording.
        recordingRequestStatus: Updated request status.
        applicationId: Updated application ID.
        externalBotId: Updated external bot ID.
        externalRecordingId: Updated external recording ID.
        startedAt: Updated start time (ISO 8601 with UTC offset).
        endedAt: Updated end time (ISO 8601 with UTC offset).
        calendarEventId: Updated associated calendar event ID.
    """
    params = UpdateCallRecordingParam(
        title=title, status=status, recordingRequestStatus=recordingRequestStatus,
        applicationId=applicationId, externalBotId=externalBotId,
        externalRecordingId=externalRecordingId, startedAt=startedAt,
        endedAt=endedAt, calendarEventId=calendarEventId,
    )
    payload = _build_payload(params)
    return await get_client().update_call_recordings(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_call_recording_by_id(id: str = "", ctx: Context = None) -> dict[str, Any]:
    """Delete a call recording by its ID (hard destroy).

    Args:
        id: The unique ID of the call recording to delete (required).
    """
    await get_client().delete_call_recording_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_call_recordings(ids: list[str] = [], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete call recordings by IDs (hard destroy).

    Args:
        ids: List of call recording IDs to delete (required).
    """
    await get_client().delete_call_recordings(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Server Status Tool
# =============================================================================
@mcp.tool()
async def check_server_status(ctx: Context = None) -> dict[str, Any]:
    """Check connectivity to the Twenty backend API."""
    import httpx
    client = get_client()
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            response = await http_client.get(
                f"{client.base_url}/rest/companies",
                headers={"Authorization": f"Bearer {get_user_token()}"}
            )
            return {"status": "connected", "backend_response": response.status_code}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


# =============================================================================
# Entry Point
# =============================================================================
def main():
    if not os.getenv("Twenty_BASE_URL"):
        print("ERROR: Twenty_BASE_URL environment variable is required", file=sys.stderr)
        print("Example: export Twenty_BASE_URL=http://twenty-app:3000/rest/", file=sys.stderr)
        sys.exit(1)

    port_env = os.getenv("MCP_SERVER_PORT")
    if not port_env:
        print("ERROR: MCP_SERVER_PORT environment variable is required", file=sys.stderr)
        print("Example: export MCP_SERVER_PORT=6375", file=sys.stderr)
        sys.exit(1)

    host = "0.0.0.0"
    port = int(port_env)
    path = "/mcp"
    app = mcp.http_app(path=path)
    app = AuthMiddleware(app)
    print(f"Starting Twenty MCP server on http://{host}:{port}{path}")
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()