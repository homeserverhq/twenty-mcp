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
# Structured JSON Models — used as tool parameters for clarity
# =============================================================================


class FullNameModel(BaseModel):
    """First and last name for a person or workspace member."""

    firstName: str  # Given name (required).
    lastName: str  # Family name (required).


class LinkModel(BaseModel):
    """A URL-based link with an optional label. Used for domainName, linkedinLink, conferenceLink."""

    primaryLinkUrl: str  # The URL string (required).
    primaryLinkLabel: str = ""  # Optional display label for the link.


class AddressModel(BaseModel):
    """Physical address with optional lat/lng coordinates."""

    addressStreet1: str = ""  # Street address line 1 (e.g. 123 Main St).
    addressStreet2: str = ""  # Street address line 2 (e.g. Apt 4B).
    addressCity: str = ""     # City name.
    addressState: str = ""    # State, province, or region code.
    addressCountry: str = ""  # Country code or full name.
    addressPostcode: str = "" # Postal / ZIP code.
    addressLat: float | None = None  # Latitude in decimal degrees.
    addressLng: float | None = None  # Longitude in decimal degrees.


class MoneyModel(BaseModel):
    """Monetary value with currency. Used for amount, annualRevenue."""

    amountMicros: int = 0  # Amount in micro-units (1 USD = 1000000 micro). E.g. $50.00 = 50000000.
    currencyCode: str = "USD"  # ISO 4217 currency code.


class EmailsModel(BaseModel):
    """Email addresses with optional additional emails."""

    primaryEmail: str  # Primary email address (required).
    additionalEmails: list[str] = []  # Additional email addresses.


class PhonesModel(BaseModel):
    """Primary phone number with country code. No additional phones exposed."""

    primaryPhoneNumber: str = ""  # Phone number (E.164 format recommended, e.g. +14155551234).
    primaryPhoneCountryCode: str = ""  # Country code (e.g. "1" for US/CAN).


def _wrap_markdown(markdown: str | None) -> dict | None:
    """Wrap a markdown string into a bodyV2 JSON structure for the backend."""
    if markdown:
        return {"markdown": markdown}
    return None


# =============================================================================
# Pydantic Contract Models — Company
# =============================================================================
class CreateCompanyParam(BaseModel):
    name: str
    domainName: LinkModel | None = None


class UpdateCompanyParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    domainName: LinkModel | None = None
    address: AddressModel | None = None
    linkedinLink: LinkModel | None = None
    annualRevenue: MoneyModel | None = None
    accountOwnerId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Person
# =============================================================================
class CreatePersonParam(BaseModel):
    name: FullNameModel
    emails: EmailsModel
    jobTitle: str = ""
    companyId: str = ""
    avatarUrl: str = ""
    position: int = 0


class UpdatePersonParam(BaseModel):
    id: Optional[str] = None
    name: FullNameModel | None = None
    emails: EmailsModel | None = None
    phones: PhonesModel | None = None
    jobTitle: Optional[str] = None
    linkedinLink: LinkModel | None = None
    companyId: Optional[str] = None
    avatarUrl: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Opportunity
# =============================================================================
class CreateOpportunityParam(BaseModel):
    name: str
    amount: MoneyModel | None = None
    closeDate: str = ""
    stage: str


class UpdateOpportunityParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    amount: MoneyModel | None = None
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
    title: str
    bodyV2: dict | None = None


class UpdateNoteParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    bodyV2: dict | None = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Task
# =============================================================================
class CreateTaskParam(BaseModel):
    title: str
    bodyV2: dict | None = None
    status: str
    dueAt: str = ""
    assigneeId: str = ""


class UpdateTaskParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    bodyV2: dict | None = None
    status: Optional[str] = None
    dueAt: Optional[str] = None
    assigneeId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — Workflow
# =============================================================================
class CreateWorkflowParam(BaseModel):
    name: str
    statuses: list[str]


class UpdateWorkflowParam(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    statuses: Optional[list[str]] = None
    lastPublishedVersionId: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — WorkspaceMember
# =============================================================================
class UpdateWorkspaceMemberParam(BaseModel):
    id: Optional[str] = None
    name: FullNameModel | None = None
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
    name: str
    fullPath: str = ""
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
    noteId: str
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
    taskId: str
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
    name: str
    happensAt: str
    targetCompanyId: str = ""
    linkedRecordId: str = ""
    linkedObjectMetadataId: str = ""
    workspaceMemberId: str = ""


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
    title: str
    startsAt: str
    endsAt: str
    description: str = ""
    location: str = ""
    conferenceLink: LinkModel | None = None


class UpdateCalendarEventParam(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    isCanceled: Optional[bool] = None
    isFullDay: Optional[bool] = None
    location: Optional[str] = None
    conferenceLink: LinkModel | None = None
    iCalUid: Optional[str] = None
    position: Optional[int] = None


# =============================================================================
# Pydantic Contract Models — CalendarEventParticipant
# =============================================================================
class CreateCalendarEventParticipantParam(BaseModel):
    calendarEventId: str
    handle: str
    displayName: str
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
    subject: str


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
    subject: str


class UpdateMessageThreadParam(BaseModel):
    id: Optional[str] = None
    subject: Optional[str] = None


# =============================================================================
# Pydantic Contract Models — MessageParticipant
# =============================================================================
class CreateMessageParticipantParam(BaseModel):
    messageId: str
    role: str
    handle: str
    displayName: str
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
    title: str
    status: str


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


def _build_payload(params: BaseModel) -> dict[str, Any]:
    payload = {}
    for k, v in params.model_dump(exclude_defaults=True).items():
        if k == "id":
            continue
        if v is None:
            continue
        if isinstance(v, str) and v.startswith("{"):
            payload[k] = _parse_json_field(v)
        elif isinstance(v, str) and v.startswith("["):
            payload[k] = _parse_json_field(v)
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
    name: str,
    domainName: LinkModel | None = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new company record.

    Args:
        name: Name of the company (required).
        domainName: Domain name link with primaryLinkUrl and optional primaryLinkLabel. (optional)
    """
    params = CreateCompanyParam(name=name, domainName=domainName)
    payload = _build_payload(params)
    return await get_client().create_company(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_company(
    id: str,
    name: Optional[str] = None,
    domainName: LinkModel | None = None,
    address: AddressModel | None = None,
    linkedinLink: LinkModel | None = None,
    annualRevenue: MoneyModel | None = None,
    accountOwnerId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing company record.

    Args:
        id: The unique ID of the company to update (required).
        name: Updated name of the company. (optional)
        domainName: Updated domain name link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        address: Updated physical address with street/city/state/country/postcode/lat/lng. (optional)
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        annualRevenue: Updated annual revenue with amountMicros and currencyCode. (optional)
        accountOwnerId: Updated account owner workspace member ID. (optional)
        position: Display sort order (lower values appear first). (optional)
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
    ids: list[str],
    name: Optional[str] = None,
    domainName: LinkModel | None = None,
    address: AddressModel | None = None,
    linkedinLink: LinkModel | None = None,
    annualRevenue: MoneyModel | None = None,
    accountOwnerId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update company records by IDs.

    Args:
        ids: List of company IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        name: Updated name for all selected companies. (optional)
        domainName: Updated domain name link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        address: Updated physical address with street/city/state/country/postcode/lat/lng. (optional)
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        annualRevenue: Updated annual revenue with amountMicros and currencyCode. (optional)
        accountOwnerId: Updated account owner workspace member ID. (optional)
        position: Display sort order (lower values appear first). (optional)
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
async def delete_company_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a company by its ID (hard destroy).

    Args:
        id: The unique ID of the company to delete (required).
    """
    await get_client().delete_company_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_companies(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete companies by IDs (hard destroy).

    Args:
        ids: List of company IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    name: FullNameModel,
    emails: EmailsModel,
    jobTitle: str = "",
    companyId: str = "",
    avatarUrl: str = "",
    position: int = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new person record.

    Args:
        name: Full name with firstName and lastName (required).
        emails: Email addresses with primaryEmail and optional additionalEmails (required).
        jobTitle: Job title of the person. (optional)
        companyId: ID of the associated company. (optional)
        avatarUrl: URL to the person's avatar image. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    params = CreatePersonParam(
        name=name, emails=emails, jobTitle=jobTitle, companyId=companyId,
        avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_person(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_person(
    id: str,
    name: FullNameModel | None = None,
    emails: EmailsModel | None = None,
    phones: PhonesModel | None = None,
    jobTitle: Optional[str] = None,
    linkedinLink: LinkModel | None = None,
    companyId: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing person record.

    Args:
        id: The unique ID of the person to update (required).
        name: Updated full name with firstName and lastName. (optional)
        emails: Updated email addresses with primaryEmail and optional additionalEmails. (optional)
        phones: Updated phone with primaryPhoneNumber and primaryPhoneCountryCode. (optional)
        jobTitle: Updated job title. (optional)
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        companyId: Updated associated company ID. (optional)
        avatarUrl: Updated avatar URL. (optional)
        position: Display sort order (lower values appear first). (optional)
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
    ids: list[str],
    name: FullNameModel | None = None,
    emails: EmailsModel | None = None,
    phones: PhonesModel | None = None,
    jobTitle: Optional[str] = None,
    linkedinLink: LinkModel | None = None,
    companyId: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update person records by IDs.

    Args:
        ids: List of person IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        name: Updated full name with firstName and lastName. (optional)
        emails: Updated email addresses with primaryEmail and optional additionalEmails. (optional)
        phones: Updated phone with primaryPhoneNumber and primaryPhoneCountryCode. (optional)
        jobTitle: Updated job title. (optional)
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        companyId: Updated associated company ID. (optional)
        avatarUrl: Updated avatar URL. (optional)
        position: Display sort order (lower values appear first). (optional)
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
async def delete_person_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a person by their ID (hard destroy).

    Args:
        id: The unique ID of the person to delete (required).
    """
    await get_client().delete_person_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_people(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete people by IDs (hard destroy).

    Args:
        ids: List of person IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    name: str,
    stage: str,
    amount: MoneyModel | None = None,
    closeDate: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new opportunity record.

    Args:
        name: Name of the opportunity (required).
        stage: Pipeline stage (e.g. NEW, SCREENING, MEETING, PROPOSAL) (required).
        amount: Monetary amount with amountMicros and currencyCode. (optional)
        closeDate: ISO 8601 date string for expected close date (e.g. 2025-12-31T23:59:59Z). (optional)
    """
    params = CreateOpportunityParam(name=name, amount=amount, closeDate=closeDate, stage=stage)
    payload = _build_payload(params)
    return await get_client().create_opportunity(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_opportunity(
    id: str,
    name: Optional[str] = None,
    amount: MoneyModel | None = None,
    closeDate: Optional[str] = None,
    stage: Optional[str] = None,
    companyId: Optional[str] = None,
    pointOfContactId: Optional[str] = None,
    ownerId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing opportunity record.

    Args:
        id: The unique ID of the opportunity to update (required).
        name: Updated name of the opportunity. (optional)
        amount: Updated monetary amount with amountMicros and currencyCode. (optional)
        closeDate: Updated ISO 8601 date string for expected close date. (optional)
    """
    params = UpdateOpportunityParam(
        name=name, amount=amount, closeDate=closeDate, stage=stage,
        companyId=companyId, pointOfContactId=pointOfContactId, ownerId=ownerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_opportunity(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_opportunities(
    ids: list[str],
    name: Optional[str] = None,
    amount: MoneyModel | None = None,
    closeDate: Optional[str] = None,
    stage: Optional[str] = None,
    companyId: Optional[str] = None,
    pointOfContactId: Optional[str] = None,
    ownerId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update opportunity records by IDs.

    Args:
        ids: List of opportunity IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        name: Updated name of the opportunity. (optional)
        amount: Updated monetary amount with amountMicros and currencyCode. (optional)
        closeDate: Updated ISO 8601 date string for expected close date. (optional)
        stage: Updated pipeline stage. (optional)
        companyId: Updated associated company ID. (optional)
        pointOfContactId: Updated associated person ID. (optional)
        ownerId: Updated owner workspace member ID. (optional)
        position: Display sort order (lower values appear first). (optional)
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
async def delete_opportunity_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete an opportunity by its ID (hard destroy).

    Args:
        id: The unique ID of the opportunity to delete (required).
    """
    await get_client().delete_opportunity_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_opportunities(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete opportunities by IDs (hard destroy).

    Args:
        ids: List of opportunity IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    title: str,
    markdown: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new note record.

    Args:
        title: Title of the note (required).
        markdown: Markdown-formatted body text for the note. (optional)
    """
    params = CreateNoteParam(title=title, bodyV2=_wrap_markdown(markdown))
    payload = _build_payload(params)
    return await get_client().create_note(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_note(
    id: str,
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing note record.

    Args:
        id: The unique ID of the note to update (required).
        title: Updated title of the note. (optional)
        markdown: Updated markdown-formatted body text. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateNoteParam(id=id, title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().update_note(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_notes(
    ids: list[str],
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update note records by IDs.

    Args:
        ids: List of note IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        title: Updated title of the note. (optional)
        markdown: Updated markdown-formatted body text. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateNoteParam(title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().update_notes(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_note_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a note by its ID (hard destroy).

    Args:
        id: The unique ID of the note to delete (required).
    """
    await get_client().delete_note_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_notes(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete notes by IDs (hard destroy).

    Args:
        ids: List of note IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    title: str,
    status: str,
    markdown: str = "",
    dueAt: str = "",
    assigneeId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new task record.

    Args:
        title: Title of the task (required).
        status: Task status (e.g. TODO, IN_PROGRESS, DONE) (required).
        markdown: Markdown-formatted body text for the task. (optional)
        dueAt: Due date (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        assigneeId: ID of the workspace member assigned to this task. (optional)
    """
    params = CreateTaskParam(
        title=title, bodyV2=_wrap_markdown(markdown), status=status, dueAt=dueAt,
        assigneeId=assigneeId,
    )
    payload = _build_payload(params)
    return await get_client().create_task(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_task(
    id: str,
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    status: Optional[str] = None,
    dueAt: Optional[str] = None,
    assigneeId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing task record.

    Args:
        id: The unique ID of the task to update (required).
        title: Updated title of the task. (optional)
        markdown: Updated markdown-formatted body text. (optional)
        status: Updated task status. (optional)
        dueAt: Updated due date (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        assigneeId: Updated assignee workspace member ID. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
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
    ids: list[str],
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    status: Optional[str] = None,
    dueAt: Optional[str] = None,
    assigneeId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update task records by IDs.

    Args:
        ids: List of task IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        title: Updated title of the task. (optional)
        markdown: Updated markdown-formatted body text. (optional)
        status: Updated task status. (optional)
        dueAt: Updated due date (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        assigneeId: Updated assignee workspace member ID. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateTaskParam(
        title=title, bodyV2=bodyV2, status=status, dueAt=dueAt,
        assigneeId=assigneeId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_tasks(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_task_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a task by its ID (hard destroy).

    Args:
        id: The unique ID of the task to delete (required).
    """
    await get_client().delete_task_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_tasks(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete tasks by IDs (hard destroy).

    Args:
        ids: List of task IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    name: str,
    statuses: list[str],
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new workflow record.

    Args:
        name: Name of the workflow (required).
        statuses: List of workflow statuses (e.g. ["ACTIVE"]) (required).
    """
    params = CreateWorkflowParam(name=name, statuses=statuses)
    payload = _build_payload(params)
    return await get_client().create_workflow(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_workflow(
    id: str,
    name: Optional[str] = None,
    statuses: list[str] = None,
    lastPublishedVersionId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing workflow record.

    Args:
        id: The unique ID of the workflow to update (required).
        name: Updated name of the workflow. (optional)
        statuses: Updated list of workflow statuses. (optional)
        lastPublishedVersionId: Updated last published version ID. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    params = UpdateWorkflowParam(
        id=id, name=name, statuses=statuses, lastPublishedVersionId=lastPublishedVersionId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workflow(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_workflow_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
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
    id: str,
    name: FullNameModel | None = None,
    colorScheme: Optional[str] = None,
    locale: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    userEmail: Optional[str] = None,
    calendarStartDay: Optional[int] = None,
    timeZone: Optional[str] = None,
    dateFormat: Optional[str] = None,
    timeFormat: Optional[str] = None,
    numberFormat: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing workspace member record.

    Args:
        id: The unique ID of the workspace member to update (required).
        name: Updated full name with firstName and lastName. (optional)
        colorScheme: Updated UI color scheme (e.g. Light, Dark, System) (optional).
        locale: Updated locale code (e.g. en_US) (optional).
        avatarUrl: Updated avatar URL. (optional)
        userEmail: Updated user email address. (optional)
        calendarStartDay: Updated first day of the week (0=Sunday, 1=Monday, etc.) (optional).
        timeZone: Updated timezone string. (optional)
        dateFormat: Updated date format preference (optional).
        timeFormat: Updated time format preference (optional).
        numberFormat: Updated number format preference (optional).
        position: Display sort order (lower values appear first). (optional)
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
    ids: list[str],
    name: FullNameModel | None = None,
    colorScheme: Optional[str] = None,
    locale: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    userEmail: Optional[str] = None,
    calendarStartDay: Optional[int] = None,
    timeZone: Optional[str] = None,
    dateFormat: Optional[str] = None,
    timeFormat: Optional[str] = None,
    numberFormat: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update workspace member records by IDs.

    Args:
        ids: List of workspace member IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        name: Updated full name with firstName and lastName. (optional)
        colorScheme: Updated UI color scheme (e.g. Light, Dark, System) (optional).
        locale: Updated locale code (e.g. en_US) (optional).
        avatarUrl: Updated avatar URL. (optional)
        userEmail: Updated user email address. (optional)
        calendarStartDay: Updated first day of the week (0=Sunday, 1=Monday, etc.) (optional).
        timeZone: Updated timezone string. (optional)
        dateFormat: Updated date format preference (optional).
        timeFormat: Updated time format preference (optional).
        numberFormat: Updated number format preference (optional).
        position: Display sort order (lower values appear first). (optional)
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
    name: str,
    fullPath: str = "",
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
        name: Name of the attachment file (required).
        fullPath: Full file path. (optional)
        targetTaskId: ID of the associated task. (optional)
        targetNoteId: ID of the associated note. (optional)
        targetPersonId: ID of the associated person. (optional)
        targetCompanyId: ID of the associated company. (optional)
        targetOpportunityId: ID of the associated opportunity. (optional)
        targetDashboardId: ID of the associated dashboard. (optional)
        targetWorkflowId: ID of the associated workflow. (optional)
    """
    params = CreateAttachmentParam(
        name=name, fullPath=fullPath,
        targetTaskId=targetTaskId, targetNoteId=targetNoteId,
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
    id: str,
    name: Optional[str] = None,
    fullPath: Optional[str] = None,
    type: Optional[str] = None,
    fileCategory: Optional[str] = None,
    authorId: Optional[str] = None,
    targetTaskId: Optional[str] = None,
    targetNoteId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    targetDashboardId: Optional[str] = None,
    targetWorkflowId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing attachment record.

    Args:
        id: The unique ID of the attachment to update (required).
        name: Updated name of the attachment file. (optional)
        fullPath: Updated full file path. (optional)
        type: Updated MIME type of the file. (optional)
        fileCategory: Updated category of the file. (optional)
        authorId: Updated author workspace member ID. (optional)
        targetTaskId: Updated associated task ID. (optional)
        targetNoteId: Updated associated note ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
        targetDashboardId: Updated associated dashboard ID. (optional)
        targetWorkflowId: Updated associated workflow ID. (optional)
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
    ids: list[str],
    name: Optional[str] = None,
    fullPath: Optional[str] = None,
    type: Optional[str] = None,
    fileCategory: Optional[str] = None,
    authorId: Optional[str] = None,
    targetTaskId: Optional[str] = None,
    targetNoteId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    targetDashboardId: Optional[str] = None,
    targetWorkflowId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update attachment records by IDs.

    Args:
        ids: List of attachment IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        name: Updated name of the attachment file. (optional)
        fullPath: Updated full file path. (optional)
        type: Updated MIME type of the file. (optional)
        fileCategory: Updated category of the file. (optional)
        authorId: Updated author workspace member ID. (optional)
        targetTaskId: Updated associated task ID. (optional)
        targetNoteId: Updated associated note ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
        targetDashboardId: Updated associated dashboard ID. (optional)
        targetWorkflowId: Updated associated workflow ID. (optional)
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
async def delete_attachment_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete an attachment by its ID (hard destroy).

    Args:
        id: The unique ID of the attachment to delete (required).
    """
    await get_client().delete_attachment_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_attachments(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete attachments by IDs (hard destroy).

    Args:
        ids: List of attachment IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    noteId: str,
    targetPersonId: str = "",
    targetCompanyId: str = "",
    targetOpportunityId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new note target record.

    Args:
        noteId: ID of the associated note (required).
        targetPersonId: ID of the associated person. (optional)
        targetCompanyId: ID of the associated company. (optional)
        targetOpportunityId: ID of the associated opportunity. (optional)
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
    id: str,
    noteId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing note target record.

    Args:
        id: The unique ID of the note target to update (required).
        noteId: Updated associated note ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
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
    ids: list[str],
    noteId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update note target records by IDs.

    Args:
        ids: List of note target IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        noteId: Updated associated note ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
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
async def delete_note_target_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a note target by its ID (hard destroy).

    Args:
        id: The unique ID of the note target to delete (required).
    """
    await get_client().delete_note_target_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_note_targets(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete note targets by IDs (hard destroy).

    Args:
        ids: List of note target IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    taskId: str,
    targetPersonId: str = "",
    targetCompanyId: str = "",
    targetOpportunityId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new task target record.

    Args:
        taskId: ID of the associated task (required).
        targetPersonId: ID of the associated person. (optional)
        targetCompanyId: ID of the associated company. (optional)
        targetOpportunityId: ID of the associated opportunity. (optional)
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
    id: str,
    taskId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing task target record.

    Args:
        id: The unique ID of the task target to update (required).
        taskId: Updated associated task ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
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
    ids: list[str],
    taskId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update task target records by IDs.

    Args:
        ids: List of task target IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        taskId: Updated associated task ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
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
async def delete_task_target_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a task target by its ID (hard destroy).

    Args:
        id: The unique ID of the task target to delete (required).
    """
    await get_client().delete_task_target_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_task_targets(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete task targets by IDs (hard destroy).

    Args:
        ids: List of task target IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    name: str,
    happensAt: str,
    targetCompanyId: str = "",
    linkedRecordId: str = "",
    linkedObjectMetadataId: str = "",
    workspaceMemberId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new timeline activity record.

    Args:
        name: Name of the activity (required).
        happensAt: When the activity occurred (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (required).
        targetCompanyId: ID of the associated company. (optional)
        linkedRecordId: ID of a linked record (e.g. calendar event). (optional)
        linkedObjectMetadataId: Metadata ID for the linked record type. (optional)
        workspaceMemberId: ID of the workspace member who performed the activity. (optional)
    """
    params = CreateTimelineActivityParam(
        name=name, happensAt=happensAt, targetCompanyId=targetCompanyId,
        linkedRecordId=linkedRecordId, linkedObjectMetadataId=linkedObjectMetadataId,
        workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().create_timeline_activity(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_timeline_activity(
    id: str,
    name: Optional[str] = None,
    happensAt: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    linkedRecordId: Optional[str] = None,
    linkedObjectMetadataId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    targetNoteId: Optional[str] = None,
    targetTaskId: Optional[str] = None,
    targetWorkflowId: Optional[str] = None,
    targetWorkflowVersionId: Optional[str] = None,
    targetWorkflowRunId: Optional[str] = None,
    targetDashboardId: Optional[str] = None,
    targetMessageListId: Optional[str] = None,
    targetMessageCampaignId: Optional[str] = None,
    properties: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing timeline activity record.

    Args:
        id: The unique ID of the timeline activity to update (required).
        name: Updated name of the activity. (optional)
        happensAt: Updated occurrence time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        workspaceMemberId: Updated associated workspace member ID. (optional)
        linkedRecordId: Updated linked record ID. (optional)
        linkedObjectMetadataId: Updated metadata ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
        targetNoteId: Updated associated note ID. (optional)
        targetTaskId: Updated associated task ID. (optional)
        targetWorkflowId: Updated associated workflow ID. (optional)
        targetWorkflowVersionId: Updated associated workflow version ID. (optional)
        targetWorkflowRunId: Updated associated workflow run ID. (optional)
        targetDashboardId: Updated associated dashboard ID. (optional)
        targetMessageListId: Updated associated message list ID. (optional)
        targetMessageCampaignId: Updated associated message campaign ID. (optional)
        properties: Updated properties as JSON string. (optional)
        position: Display sort order (lower values appear first). (optional)
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
    ids: list[str],
    name: Optional[str] = None,
    happensAt: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    linkedRecordId: Optional[str] = None,
    linkedObjectMetadataId: Optional[str] = None,
    targetPersonId: Optional[str] = None,
    targetCompanyId: Optional[str] = None,
    targetOpportunityId: Optional[str] = None,
    targetNoteId: Optional[str] = None,
    targetTaskId: Optional[str] = None,
    targetWorkflowId: Optional[str] = None,
    targetWorkflowVersionId: Optional[str] = None,
    targetWorkflowRunId: Optional[str] = None,
    targetDashboardId: Optional[str] = None,
    targetMessageListId: Optional[str] = None,
    targetMessageCampaignId: Optional[str] = None,
    properties: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update timeline activity records by IDs.

    Args:
        ids: List of timeline activity IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        name: Updated name of the activity. (optional)
        happensAt: Updated occurrence time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        workspaceMemberId: Updated associated workspace member ID. (optional)
        linkedRecordId: Updated linked record ID. (optional)
        linkedObjectMetadataId: Updated metadata ID. (optional)
        targetPersonId: Updated associated person ID. (optional)
        targetCompanyId: Updated associated company ID. (optional)
        targetOpportunityId: Updated associated opportunity ID. (optional)
        targetNoteId: Updated associated note ID. (optional)
        targetTaskId: Updated associated task ID. (optional)
        targetWorkflowId: Updated associated workflow ID. (optional)
        targetWorkflowVersionId: Updated associated workflow version ID. (optional)
        targetWorkflowRunId: Updated associated workflow run ID. (optional)
        targetDashboardId: Updated associated dashboard ID. (optional)
        targetMessageListId: Updated associated message list ID. (optional)
        targetMessageCampaignId: Updated associated message campaign ID. (optional)
        properties: Updated properties as JSON string. (optional)
        position: Display sort order (lower values appear first). (optional)
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
async def delete_timeline_activity_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a timeline activity by its ID (hard destroy).

    Args:
        id: The unique ID of the timeline activity to delete (required).
    """
    await get_client().delete_timeline_activity_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_timeline_activities(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete timeline activities by IDs (hard destroy).

    Args:
        ids: List of timeline activity IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    title: str,
    startsAt: str,
    endsAt: str,
    description: str = "",
    location: str = "",
    conferenceLink: LinkModel | None = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new calendar event record.

    Args:
        title: Title of the calendar event (required).
        startsAt: Start time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (required).
        endsAt: End time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (required).
        description: Description of the event. (optional)
        location: Event location as plain text. (optional)
        conferenceLink: Conference link with primaryLinkUrl and optional primaryLinkLabel. (optional)
    """
    params = CreateCalendarEventParam(
        title=title, startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().create_calendar_event(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_calendar_event(
    id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    startsAt: Optional[str] = None,
    endsAt: Optional[str] = None,
    isCanceled: Optional[bool] = None,
    isFullDay: Optional[bool] = None,
    location: Optional[str] = None,
    conferenceLink: LinkModel | None = None,
    iCalUid: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing calendar event record.

    Args:
        id: The unique ID of the calendar event to update (required).
        title: Updated title of the calendar event. (optional)
        description: Updated description. (optional)
        startsAt: Updated start time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        endsAt: Updated end time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        isCanceled: Updated cancellation status. (optional)
        isFullDay: Updated all-day flag. (optional)
        location: Updated event location as plain text. (optional)
        conferenceLink: Updated conference link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        iCalUid: Updated iCal UID. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    params = UpdateCalendarEventParam(
        id=id, title=title, isCanceled=isCanceled, isFullDay=isFullDay,
        startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, iCalUid=iCalUid, conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_event(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_calendar_events(
    ids: list[str],
    title: Optional[str] = None,
    description: Optional[str] = None,
    startsAt: Optional[str] = None,
    endsAt: Optional[str] = None,
    isCanceled: Optional[bool] = None,
    isFullDay: Optional[bool] = None,
    location: Optional[str] = None,
    conferenceLink: LinkModel | None = None,
    iCalUid: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update calendar event records by IDs.

    Args:
        ids: List of calendar event IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        title: Updated title of the calendar event. (optional)
        description: Updated description. (optional)
        startsAt: Updated start time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        endsAt: Updated end time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        isCanceled: Updated cancellation status. (optional)
        isFullDay: Updated all-day flag. (optional)
        location: Updated event location as plain text. (optional)
        conferenceLink: Updated conference link with primaryLinkUrl and optional primaryLinkLabel. (optional)
        iCalUid: Updated iCal UID. (optional)
        position: Display sort order (lower values appear first). (optional)
    """
    params = UpdateCalendarEventParam(
        title=title, isCanceled=isCanceled, isFullDay=isFullDay,
        startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, iCalUid=iCalUid, conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_events(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_calendar_event_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a calendar event by its ID (hard destroy).

    Args:
        id: The unique ID of the calendar event to delete (required).
    """
    await get_client().delete_calendar_event_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_calendar_events(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete calendar events by IDs (hard destroy).

    Args:
        ids: List of calendar event IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    calendarEventId: str,
    handle: str,
    displayName: str,
    isOrganizer: bool = False,
    responseStatus: str = "NEEDS_ACTION",
    personId: str = "",
    workspaceMemberId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new calendar event participant record.

    Args:
        calendarEventId: ID of the associated calendar event (required).
        handle: Email handle of the participant (required).
        displayName: Display name of the participant (required).
        isOrganizer: Whether this participant is the organizer. (optional)
        responseStatus: Response status (NEEDS_ACTION, DECLINED, TENTATIVE, ACCEPTED). (optional)
        personId: ID of the associated person. (optional)
        workspaceMemberId: ID of the associated workspace member. (optional)
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
    id: str,
    calendarEventId: Optional[str] = None,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    isOrganizer: Optional[bool] = None,
    responseStatus: Optional[str] = None,
    personId: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing calendar event participant record.

    Args:
        id: The unique ID of the calendar event participant to update (required).
        calendarEventId: Updated associated calendar event ID. (optional)
        handle: Updated email handle. (optional)
        displayName: Updated display name. (optional)
        isOrganizer: Updated organizer flag. (optional)
        responseStatus: Updated response status (NEEDS_ACTION, DECLINED, TENTATIVE, ACCEPTED) (optional).
        personId: Updated associated person ID. (optional)
        workspaceMemberId: Updated associated workspace member ID. (optional)
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
    ids: list[str],
    calendarEventId: Optional[str] = None,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    isOrganizer: Optional[bool] = None,
    responseStatus: Optional[str] = None,
    personId: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update calendar event participant records by IDs.

    Args:
        ids: List of calendar event participant IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        calendarEventId: Updated associated calendar event ID. (optional)
        handle: Updated email handle. (optional)
        displayName: Updated display name. (optional)
        isOrganizer: Updated organizer flag. (optional)
        responseStatus: Updated response status (NEEDS_ACTION, DECLINED, TENTATIVE, ACCEPTED) (optional).
        personId: Updated associated person ID. (optional)
        workspaceMemberId: Updated associated workspace member ID. (optional)
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
async def delete_calendar_event_participant_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a calendar event participant by its ID (hard destroy).

    Args:
        id: The unique ID of the calendar event participant to delete (required).
    """
    await get_client().delete_calendar_event_participant_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_calendar_event_participants(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete calendar event participants by IDs (hard destroy).

    Args:
        ids: List of calendar event participant IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    subject: str,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message record.

    Args:
        subject: Subject of the message (required).
    """
    params = CreateMessageParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().create_message(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message(
    id: str,
    headerMessageId: Optional[str] = None,
    subject: Optional[str] = None,
    text: Optional[str] = None,
    receivedAt: Optional[str] = None,
    messageThreadId: Optional[str] = None,
    messageCampaignId: Optional[str] = None,
    deliveryStatus: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message record.

    Args:
        id: The unique ID of the message to update (required).
        headerMessageId: Updated header message ID. (optional)
        subject: Updated subject of the message. (optional)
        text: Updated body text of the message. (optional)
        receivedAt: Updated received timestamp (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        messageThreadId: Updated associated message thread ID. (optional)
        messageCampaignId: Updated associated message campaign ID. (optional)
        deliveryStatus: Updated delivery status. (optional)
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
    ids: list[str],
    headerMessageId: Optional[str] = None,
    subject: Optional[str] = None,
    text: Optional[str] = None,
    receivedAt: Optional[str] = None,
    messageThreadId: Optional[str] = None,
    messageCampaignId: Optional[str] = None,
    deliveryStatus: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message records by IDs.

    Args:
        ids: List of message IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        headerMessageId: Updated header message ID. (optional)
        subject: Updated subject of the message. (optional)
        text: Updated body text of the message. (optional)
        receivedAt: Updated received timestamp (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        messageThreadId: Updated associated message thread ID. (optional)
        messageCampaignId: Updated associated message campaign ID. (optional)
        deliveryStatus: Updated delivery status. (optional)
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
async def delete_message_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a message by its ID (hard destroy).

    Args:
        id: The unique ID of the message to delete (required).
    """
    await get_client().delete_message_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_messages(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete messages by IDs (hard destroy).

    Args:
        ids: List of message IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    subject: str,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message thread record.

    Args:
        subject: Subject of the message thread (required).
    """
    params = CreateMessageThreadParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().create_message_thread(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message_thread(
    id: str,
    subject: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message thread record.

    Args:
        id: The unique ID of the message thread to update (required).
        subject: Updated subject of the message thread. (optional)
    """
    params = UpdateMessageThreadParam(id=id, subject=subject)
    payload = _build_payload(params)
    return await get_client().update_message_thread(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_message_threads(
    ids: list[str],
    subject: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message thread records by IDs.

    Args:
        ids: List of message thread IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        subject: Updated subject of the message thread. (optional)
    """
    params = UpdateMessageThreadParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().update_message_threads(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def delete_message_thread_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a message thread by its ID (hard destroy).

    Args:
        id: The unique ID of the message thread to delete (required).
    """
    await get_client().delete_message_thread_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_message_threads(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete message threads by IDs (hard destroy).

    Args:
        ids: List of message thread IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    messageId: str,
    role: str,
    handle: str,
    displayName: str,
    personId: str = "",
    workspaceMemberId: str = "",
    messageCampaignId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message participant record.

    Args:
        messageId: ID of the associated message (required).
        role: Role of the participant (required).
        handle: Email handle of the participant (required).
        displayName: Display name of the participant (required).
        personId: ID of the associated person. (optional)
        workspaceMemberId: ID of the associated workspace member. (optional)
        messageCampaignId: ID of the associated message campaign. (optional)
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
    id: str,
    messageId: Optional[str] = None,
    role: Optional[str] = None,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    personId: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    messageCampaignId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message participant record.

    Args:
        id: The unique ID of the message participant to update (required).
        messageId: Updated associated message ID. (optional)
        role: Updated role of the participant. (optional)
        handle: Updated email handle. (optional)
        displayName: Updated display name. (optional)
        personId: Updated associated person ID. (optional)
        workspaceMemberId: Updated associated workspace member ID. (optional)
        messageCampaignId: Updated associated message campaign ID. (optional)
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
    ids: list[str],
    messageId: Optional[str] = None,
    role: Optional[str] = None,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    personId: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    messageCampaignId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message participant records by IDs.

    Args:
        ids: List of message participant IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        messageId: Updated associated message ID. (optional)
        role: Updated role of the participant. (optional)
        handle: Updated email handle. (optional)
        displayName: Updated display name. (optional)
        personId: Updated associated person ID. (optional)
        workspaceMemberId: Updated associated workspace member ID. (optional)
        messageCampaignId: Updated associated message campaign ID. (optional)
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
async def delete_message_participant_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a message participant by its ID (hard destroy).

    Args:
        id: The unique ID of the message participant to delete (required).
    """
    await get_client().delete_message_participant_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_message_participants(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete message participants by IDs (hard destroy).

    Args:
        ids: List of message participant IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    title: str,
    status: str,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new call recording record.

    Args:
        title: Title of the call recording (required).
        status: Status of the call recording (required).
    """
    params = CreateCallRecordingParam(title=title, status=status)
    payload = _build_payload(params)
    return await get_client().create_call_recording(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool()
async def update_call_recording(
    id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    recordingRequestStatus: Optional[str] = None,
    applicationId: Optional[str] = None,
    externalBotId: Optional[str] = None,
    externalRecordingId: Optional[str] = None,
    startedAt: Optional[str] = None,
    endedAt: Optional[str] = None,
    calendarEventId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing call recording record.

    Args:
        id: The unique ID of the call recording to update (required).
        title: Updated title of the call recording. (optional)
        status: Updated status of the call recording. (optional)
        recordingRequestStatus: Updated request status. (optional)
        applicationId: Updated application ID. (optional)
        externalBotId: Updated external bot ID. (optional)
        externalRecordingId: Updated external recording ID. (optional)
        startedAt: Updated start time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        endedAt: Updated end time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        calendarEventId: Updated associated calendar event ID. (optional)
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
    ids: list[str],
    title: Optional[str] = None,
    status: Optional[str] = None,
    recordingRequestStatus: Optional[str] = None,
    applicationId: Optional[str] = None,
    externalBotId: Optional[str] = None,
    externalRecordingId: Optional[str] = None,
    startedAt: Optional[str] = None,
    endedAt: Optional[str] = None,
    calendarEventId: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update call recording records by IDs.

    Args:
        ids: List of call recording IDs (UUID format, e.g. "a1b2c3d4-...") to update (required).
        title: Updated title of the call recording. (optional)
        status: Updated status of the call recording. (optional)
        recordingRequestStatus: Updated request status. (optional)
        applicationId: Updated application ID. (optional)
        externalBotId: Updated external bot ID. (optional)
        externalRecordingId: Updated external recording ID. (optional)
        startedAt: Updated start time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        endedAt: Updated end time (Use ISO 8601 format with explicit UTC offset (2026-06-22T15:00:00-04:00) (optional)
        calendarEventId: Updated associated calendar event ID. (optional)
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
async def delete_call_recording_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a call recording by its ID (hard destroy).

    Args:
        id: The unique ID of the call recording to delete (required).
    """
    await get_client().delete_call_recording_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool()
async def delete_call_recordings(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete call recordings by IDs (hard destroy).

    Args:
        ids: List of call recording IDs (UUID format, e.g. "a1b2c3d4-...") to delete (required).
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
    if not os.getenv("TWENTY_BASE_URL"):
        print("ERROR: TWENTY_BASE_URL environment variable is required", file=sys.stderr)
        print("Example: export TWENTY_BASE_URL=http://twenty-app:3000", file=sys.stderr)
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