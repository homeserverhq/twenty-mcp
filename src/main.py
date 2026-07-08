import os
import sys
import json
from contextvars import ContextVar
from typing import Any, Optional

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
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

    firstName: str = Field(description="Given name.")
    lastName: str = Field(description="Family name.")


class LinkModel(BaseModel):
    """A URL-based link with an optional label. Used for domainName, linkedinLink, conferenceLink."""

    primaryLinkUrl: str = Field(description="The URL string.")
    primaryLinkLabel: str = Field(default="", description="Optional display label for the link.")


class AddressModel(BaseModel):
    """Physical address with optional lat/lng coordinates."""

    addressStreet1: str = Field(default="", description="Street address line 1 (e.g. 123 Main St).")
    addressStreet2: str = Field(default="", description="Street address line 2 (e.g. Apt 4B).")
    addressCity: str = Field(default="", description="City name.")
    addressState: str = Field(default="", description="State, province, or region code.")
    addressCountry: str = Field(default="", description="Country code or full name.")
    addressPostcode: str = Field(default="", description="Postal / ZIP code.")
    addressLat: float | None = Field(default=None, description="Latitude in decimal degrees.")
    addressLng: float | None = Field(default=None, description="Longitude in decimal degrees.")


class MoneyModel(BaseModel):
    """Monetary value with currency. Used for amount, annualRevenue."""

    amountMicros: int = Field(default=0, description="Amount in micro-units (1 USD = 1000000 micro). E.g. $50.00 = 50000000.")
    currencyCode: str = Field(default="USD", description="ISO 4217 currency code.")


class EmailsModel(BaseModel):
    """Email addresses with optional additional emails."""

    primaryEmail: str = Field(description="Primary email address.")
    additionalEmails: list[str] = Field(default=[], description="Additional email addresses.")


class PhonesModel(BaseModel):
    """Primary phone number with country code. No additional phones exposed."""

    primaryPhoneNumber: str = Field(default="", description="Phone number (E.164 format recommended, e.g. +14155551234).")
    primaryPhoneCountryCode: str = Field(default="", description='Country code (e.g. "1" for US/CAN).')


class PropertiesDiffEntry(BaseModel):
    """Before/after values for a single field change in a timeline activity."""
    fieldName: str = Field(description="Name of the field that changed.")
    before: str = Field(default="", description="Previous value of the field.")
    after: str = Field(default="", description="New value of the field.")


class PropertiesModel(BaseModel):
    """Properties payload for a timeline activity event. Describes what changed in the associated record."""
    updatedFields: Optional[list[str]] = Field(default=None, description="List of field names that changed.")
    diff: Optional[list[PropertiesDiffEntry]] = Field(default=None, description="List of per-field diffs with before/after values.")


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
    position: Optional[float] = None


# =============================================================================
# Pydantic Contract Models — Person
# =============================================================================
class CreatePersonParam(BaseModel):
    name: FullNameModel
    emails: EmailsModel
    jobTitle: str = ""
    companyId: str = ""
    avatarUrl: str = ""
    position: float = 0


class UpdatePersonParam(BaseModel):
    id: Optional[str] = None
    name: FullNameModel | None = None
    emails: EmailsModel | None = None
    phones: PhonesModel | None = None
    jobTitle: Optional[str] = None
    linkedinLink: LinkModel | None = None
    companyId: Optional[str] = None
    avatarUrl: Optional[str] = None
    position: Optional[float] = None


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
    position: Optional[float] = None


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
    position: Optional[float] = None


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
    position: Optional[float] = None


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
    position: Optional[float] = None


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
    position: Optional[float] = None


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
    properties: Optional[PropertiesModel] = None
    position: Optional[float] = None


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
    position: Optional[float] = None


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
        if isinstance(v, BaseModel):
            payload[k] = v.model_dump(exclude_defaults=True)
        elif isinstance(v, str) and v.startswith("{"):
            payload[k] = _parse_json_field(v)
        elif isinstance(v, str) and v.startswith("["):
            payload[k] = _parse_json_field(v)
        else:
            payload[k] = v
    return payload


def _enum_upper(v: str | None) -> str | None:
    if v is None:
        return None
    return v.upper()


def _enum_capitalize(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip().lower()
    return s.capitalize() if s else None


def _snake_to_pascal(v: str | None) -> str | None:
    if v is None:
        return None
    return "".join(word.capitalize() for word in v.split("_"))


def _enum_upper_list(v: list[str] | None) -> list[str] | None:
    if v is None:
        return None
    return [item.upper() for item in v]


def _day_name_to_int(v: str | int | None) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    mapping = {
        "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
        "thursday": 4, "friday": 5, "saturday": 6,
    }
    return mapping.get(v.strip().lower())


# =============================================================================
# Company Tools
# =============================================================================
@mcp.tool(tags={"read", "basic", "twenty"})
async def list_companies(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all company records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_companies(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "basic", "twenty"})
async def get_company_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single company by its ID.

    Args:
        id: The unique ID of the company.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_company_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def create_company(
    name: str,
    domainName: LinkModel | None = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new company record.

    Args:
        name: Name of the company.
        domainName: Domain name link with primaryLinkUrl and optional primaryLinkLabel.
    """
    params = CreateCompanyParam(name=name, domainName=domainName)
    payload = _build_payload(params)
    return await get_client().create_company(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def update_company(
    id: str,
    name: Optional[str] = None,
    domainName: LinkModel | None = None,
    address: AddressModel | None = None,
    linkedinLink: LinkModel | None = None,
    annualRevenue: MoneyModel | None = None,
    accountOwnerId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing company record.

    Args:
        id: The unique ID of the company to update.
        name: Updated name of the company.
        domainName: Updated domain name link with primaryLinkUrl and optional primaryLinkLabel.
        address: Updated physical address with street/city/state/country/postcode/lat/lng.
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel.
        annualRevenue: Updated annual revenue with amountMicros and currencyCode.
        accountOwnerId: Updated account owner workspace member ID.
        position: Display position (0 to 1000000). Lower values appear first.
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


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_companies(
    ids: list[str],
    name: Optional[str] = None,
    domainName: LinkModel | None = None,
    address: AddressModel | None = None,
    linkedinLink: LinkModel | None = None,
    annualRevenue: MoneyModel | None = None,
    accountOwnerId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update company records by IDs.

    Args:
        ids: List of company IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        name: Updated name for all selected companies.
        domainName: Updated domain name link with primaryLinkUrl and optional primaryLinkLabel.
        address: Updated physical address with street/city/state/country/postcode/lat/lng.
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel.
        annualRevenue: Updated annual revenue with amountMicros and currencyCode.
        accountOwnerId: Updated account owner workspace member ID.
        position: Display position (0 to 1000000). Lower values appear first.
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


@mcp.tool(tags={"write", "basic", "twenty"})
async def delete_company_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a company by its ID (hard destroy).

    Args:
        id: The unique ID of the company to delete.
    """
    await get_client().delete_company_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_companies(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete companies by IDs (hard destroy).

    Args:
        ids: List of company IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_companies(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Person Tools
# =============================================================================
@mcp.tool(tags={"read", "basic", "twenty"})
async def list_people(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all person records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_people(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "basic", "twenty"})
async def get_person_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single person by their ID.

    Args:
        id: The unique ID of the person.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_person_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def create_person(
    name: FullNameModel,
    emails: EmailsModel,
    jobTitle: str = "",
    companyId: str = "",
    avatarUrl: str = "",
    position: float = 0,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new person record.

    Args:
        name: Full name with firstName and lastName.
        emails: Email addresses with primaryEmail and optional additionalEmails.
        jobTitle: Job title of the person.
        companyId: ID of the associated company.
        avatarUrl: URL to the person's avatar image.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = CreatePersonParam(
        name=name, emails=emails, jobTitle=jobTitle, companyId=companyId,
        avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().create_person(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def update_person(
    id: str,
    name: FullNameModel | None = None,
    emails: EmailsModel | None = None,
    phones: PhonesModel | None = None,
    jobTitle: Optional[str] = None,
    linkedinLink: LinkModel | None = None,
    companyId: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing person record.

    Args:
        id: The unique ID of the person to update.
        name: Updated full name with firstName and lastName.
        emails: Updated email addresses with primaryEmail and optional additionalEmails.
        phones: Updated phone with primaryPhoneNumber and primaryPhoneCountryCode.
        jobTitle: Updated job title.
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel.
        companyId: Updated associated company ID.
        avatarUrl: Updated avatar URL.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdatePersonParam(
        id=id, name=name, emails=emails, phones=phones, jobTitle=jobTitle,
        linkedinLink=linkedinLink, companyId=companyId, avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_person(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_people(
    ids: list[str],
    name: FullNameModel | None = None,
    emails: EmailsModel | None = None,
    phones: PhonesModel | None = None,
    jobTitle: Optional[str] = None,
    linkedinLink: LinkModel | None = None,
    companyId: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update person records by IDs.

    Args:
        ids: List of person IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        name: Updated full name with firstName and lastName.
        emails: Updated email addresses with primaryEmail and optional additionalEmails.
        phones: Updated phone with primaryPhoneNumber and primaryPhoneCountryCode.
        jobTitle: Updated job title.
        linkedinLink: Updated LinkedIn link with primaryLinkUrl and optional primaryLinkLabel.
        companyId: Updated associated company ID.
        avatarUrl: Updated avatar URL.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdatePersonParam(
        name=name, emails=emails, phones=phones, jobTitle=jobTitle,
        linkedinLink=linkedinLink, companyId=companyId, avatarUrl=avatarUrl, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_people(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def delete_person_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a person by their ID (hard destroy).

    Args:
        id: The unique ID of the person to delete.
    """
    await get_client().delete_person_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_people(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete people by IDs (hard destroy).

    Args:
        ids: List of person IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_people(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Opportunity Tools
# =============================================================================
@mcp.tool(tags={"read", "basic", "twenty"})
async def list_opportunities(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all opportunity records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_opportunities(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "basic", "twenty"})
async def get_opportunity_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single opportunity by its ID.

    Args:
        id: The unique ID of the opportunity.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_opportunity_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def create_opportunity(
    name: str,
    stage: str,
    amount: MoneyModel | None = None,
    closeDate: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new opportunity record.

    Args:
        name: Name of the opportunity.
        stage: new, screening, meeting, proposal, or customer
        amount: Monetary amount with amountMicros and currencyCode.
        closeDate: ISO 8601 format (2026-06-22T15:00:00-04:00).
    """
    params = CreateOpportunityParam(name=name, amount=amount, closeDate=closeDate, stage=_enum_upper(stage))
    payload = _build_payload(params)
    return await get_client().create_opportunity(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def update_opportunity(
    id: str,
    name: Optional[str] = None,
    amount: MoneyModel | None = None,
    closeDate: Optional[str] = None,
    stage: Optional[str] = None,
    companyId: Optional[str] = None,
    pointOfContactId: Optional[str] = None,
    ownerId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing opportunity record.

    Args:
        id: The unique ID of the opportunity to update.
        name: Updated name of the opportunity.
        amount: Updated monetary amount with amountMicros and currencyCode.
        closeDate: ISO 8601 format (2026-06-22T15:00:00-04:00).
        stage: new, screening, meeting, proposal, or customer
        companyId: Updated associated company ID.
        pointOfContactId: Updated associated person ID.
        ownerId: Updated owner workspace member ID.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdateOpportunityParam(
        name=name, amount=amount, closeDate=closeDate, stage=_enum_upper(stage),
        companyId=companyId, pointOfContactId=pointOfContactId, ownerId=ownerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_opportunity(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_opportunities(
    ids: list[str],
    name: Optional[str] = None,
    amount: MoneyModel | None = None,
    closeDate: Optional[str] = None,
    stage: Optional[str] = None,
    companyId: Optional[str] = None,
    pointOfContactId: Optional[str] = None,
    ownerId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update opportunity records by IDs.

    Args:
        ids: List of opportunity IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        name: Updated name of the opportunity.
        amount: Updated monetary amount with amountMicros and currencyCode.
        closeDate: ISO 8601 format (2026-06-22T15:00:00-04:00).
        stage: new, screening, meeting, proposal, or customer
        companyId: Updated associated company ID.
        pointOfContactId: Updated associated person ID.
        ownerId: Updated owner workspace member ID.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdateOpportunityParam(
        name=name, amount=amount, closeDate=closeDate, stage=_enum_upper(stage),
        companyId=companyId, pointOfContactId=pointOfContactId, ownerId=ownerId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_opportunities(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "basic", "twenty"})
async def delete_opportunity_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete an opportunity by its ID (hard destroy).

    Args:
        id: The unique ID of the opportunity to delete.
    """
    await get_client().delete_opportunity_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_opportunities(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete opportunities by IDs (hard destroy).

    Args:
        ids: List of opportunity IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_opportunities(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Note Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_notes(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all note records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_notes(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_note_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single note by its ID.

    Args:
        id: The unique ID of the note.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_note_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def create_note(
    title: str,
    markdown: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new note record.

    Args:
        title: Title of the note.
        markdown: Markdown-formatted body text for the note.
    """
    params = CreateNoteParam(title=title, bodyV2=_wrap_markdown(markdown))
    payload = _build_payload(params)
    return await get_client().create_note(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_note(
    id: str,
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing note record.

    Args:
        id: The unique ID of the note to update.
        title: Updated title of the note.
        markdown: Updated markdown-formatted body text.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateNoteParam(id=id, title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().update_note(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_notes(
    ids: list[str],
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update note records by IDs.

    Args:
        ids: List of note IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        title: Updated title of the note.
        markdown: Updated markdown-formatted body text.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateNoteParam(title=title, bodyV2=bodyV2, position=position)
    payload = _build_payload(params)
    return await get_client().update_notes(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_note_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a note by its ID (hard destroy).

    Args:
        id: The unique ID of the note to delete.
    """
    await get_client().delete_note_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_notes(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete notes by IDs (hard destroy).

    Args:
        ids: List of note IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_notes(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Task Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_tasks(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all task records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_tasks(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_task_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single task by its ID.

    Args:
        id: The unique ID of the task.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_task_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
        title: Title of the task.
        status: todo, in_progress, or done
        markdown: Markdown-formatted body text for the task.
        dueAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        assigneeId: ID of the workspace member assigned to this task.
    """
    params = CreateTaskParam(
        title=title, bodyV2=_wrap_markdown(markdown), status=_enum_upper(status), dueAt=dueAt,
        assigneeId=assigneeId,
    )
    payload = _build_payload(params)
    return await get_client().create_task(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_task(
    id: str,
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    status: Optional[str] = None,
    dueAt: Optional[str] = None,
    assigneeId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing task record.

    Args:
        id: The unique ID of the task to update.
        title: Updated title of the task.
        markdown: Updated markdown-formatted body text.
        status: todo, in_progress, or done
        dueAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        assigneeId: Updated assignee workspace member ID.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateTaskParam(
        id=id, title=title, bodyV2=bodyV2, status=_enum_upper(status), dueAt=dueAt,
        assigneeId=assigneeId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_task(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_tasks(
    ids: list[str],
    title: Optional[str] = None,
    markdown: Optional[str] = None,
    status: Optional[str] = None,
    dueAt: Optional[str] = None,
    assigneeId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update task records by IDs.

    Args:
        ids: List of task IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        title: Updated title of the task.
        markdown: Updated markdown-formatted body text.
        status: todo, in_progress, or done
        dueAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        assigneeId: Updated assignee workspace member ID.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    bodyV2 = _wrap_markdown(markdown) if markdown else None
    params = UpdateTaskParam(
        title=title, bodyV2=bodyV2, status=_enum_upper(status), dueAt=dueAt,
        assigneeId=assigneeId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_tasks(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_task_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a task by its ID (hard destroy).

    Args:
        id: The unique ID of the task to delete.
    """
    await get_client().delete_task_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_tasks(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete tasks by IDs (hard destroy).

    Args:
        ids: List of task IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_tasks(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Workflow Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_workflows(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all workflow records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_workflows(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_workflow_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single workflow by its ID.

    Args:
        id: The unique ID of the workflow.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_workflow_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def create_workflow(
    name: str,
    statuses: list[str],
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new workflow record.

    Args:
        name: Name of the workflow.
        statuses: draft, active, or deactivated
    """
    params = CreateWorkflowParam(name=name, statuses=_enum_upper_list(statuses))
    payload = _build_payload(params)
    return await get_client().create_workflow(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def update_workflow(
    id: str,
    name: Optional[str] = None,
    statuses: list[str] = None,
    lastPublishedVersionId: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing workflow record.

    Args:
        id: The unique ID of the workflow to update.
        name: Updated name of the workflow.
        statuses: draft, active, or deactivated
        lastPublishedVersionId: Updated last published version ID.
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdateWorkflowParam(
        id=id, name=name, statuses=_enum_upper_list(statuses), lastPublishedVersionId=lastPublishedVersionId, position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workflow(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_workflow_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a workflow by its ID (hard destroy).

    Args:
        id: The unique ID of the workflow to delete.
    """
    await get_client().delete_workflow_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


# =============================================================================
# WorkspaceMember Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_workspace_members(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all workspace member records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_workspace_members(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_workspace_member_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single workspace member by their ID.

    Args:
        id: The unique ID of the workspace member.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_workspace_member_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def update_workspace_member(
    id: str,
    name: FullNameModel | None = None,
    colorScheme: Optional[str] = None,
    locale: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    userEmail: Optional[str] = None,
    calendarStartDay: Optional[str] = None,
    timeZone: Optional[str] = None,
    dateFormat: Optional[str] = None,
    timeFormat: Optional[str] = None,
    numberFormat: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing workspace member record.

    Args:
        id: The unique ID of the workspace member to update.
        name: Updated full name with firstName and lastName.
        colorScheme: light, dark, or system
        locale: Updated locale code (e.g. en_US).
        avatarUrl: Updated avatar URL.
        userEmail: Updated user email address.
        calendarStartDay: 0 to 6 (0=sunday, 1=monday, ..., 6=saturday).
        timeZone: Updated timezone string.
        dateFormat: system, month_first, day_first, or year_first
        timeFormat: system, hour_24, or hour_12
        numberFormat: system, commas_and_dot, spaces_and_comma, dots_and_comma, or apostrophe_and_dot
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdateWorkspaceMemberParam(
        id=id, name=name, colorScheme=_enum_capitalize(colorScheme), locale=locale, avatarUrl=avatarUrl,
        userEmail=userEmail, calendarStartDay=_day_name_to_int(calendarStartDay), timeZone=timeZone,
        dateFormat=_snake_to_pascal(dateFormat), timeFormat=_snake_to_pascal(timeFormat), numberFormat=_snake_to_pascal(numberFormat), position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workspace_member(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def update_workspace_members(
    ids: list[str],
    name: FullNameModel | None = None,
    colorScheme: Optional[str] = None,
    locale: Optional[str] = None,
    avatarUrl: Optional[str] = None,
    userEmail: Optional[str] = None,
    calendarStartDay: Optional[str] = None,
    timeZone: Optional[str] = None,
    dateFormat: Optional[str] = None,
    timeFormat: Optional[str] = None,
    numberFormat: Optional[str] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update workspace member records by IDs.

    Args:
        ids: List of workspace member IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        name: Updated full name with firstName and lastName.
        colorScheme: light, dark, or system
        locale: Updated locale code (e.g. en_US).
        avatarUrl: Updated avatar URL.
        userEmail: Updated user email address.
        calendarStartDay: 0 to 6 (0=sunday, 1=monday, ..., 6=saturday).
        timeZone: Updated timezone string.
        dateFormat: system, month_first, day_first, or year_first
        timeFormat: system, hour_24, or hour_12
        numberFormat: system, commas_and_dot, spaces_and_comma, dots_and_comma, or apostrophe_and_dot
        position: Display position (0 to 1000000). Lower values appear first.
    """
    params = UpdateWorkspaceMemberParam(
        name=name, colorScheme=_enum_capitalize(colorScheme), locale=locale, avatarUrl=avatarUrl,
        userEmail=userEmail, calendarStartDay=_day_name_to_int(calendarStartDay), timeZone=timeZone,
        dateFormat=_snake_to_pascal(dateFormat), timeFormat=_snake_to_pascal(timeFormat), numberFormat=_snake_to_pascal(numberFormat), position=position,
    )
    payload = _build_payload(params)
    return await get_client().update_workspace_members(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


# =============================================================================
# Attachment Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_attachments(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all attachment records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_attachments(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_attachment_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single attachment by its ID.

    Args:
        id: The unique ID of the attachment.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_attachment_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
        name: Name of the attachment file.
        fullPath: Full file path.
        targetTaskId: ID of the associated task.
        targetNoteId: ID of the associated note.
        targetPersonId: ID of the associated person.
        targetCompanyId: ID of the associated company.
        targetOpportunityId: ID of the associated opportunity.
        targetDashboardId: ID of the associated dashboard.
        targetWorkflowId: ID of the associated workflow.
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


@mcp.tool(tags={"write", "primary", "twenty"})
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
        id: The unique ID of the attachment to update.
        name: Updated name of the attachment file.
        fullPath: Updated full file path.
        type: Deprecated MIME type. Use fileCategory instead.
        fileCategory: archive, audio, image, presentation, spreadsheet, text_document, video, or other
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
        id=id, name=name, fullPath=fullPath, type=type, fileCategory=_enum_upper(fileCategory),
        authorId=authorId, targetTaskId=targetTaskId, targetNoteId=targetNoteId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetDashboardId=targetDashboardId,
        targetWorkflowId=targetWorkflowId,
    )
    payload = _build_payload(params)
    return await get_client().update_attachment(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
        ids: List of attachment IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        name: Updated name of the attachment file.
        fullPath: Updated full file path.
        type: Deprecated MIME type. Use fileCategory instead.
        fileCategory: archive, audio, image, presentation, spreadsheet, text_document, video, or other
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
        name=name, fullPath=fullPath, type=type, fileCategory=_enum_upper(fileCategory),
        authorId=authorId, targetTaskId=targetTaskId, targetNoteId=targetNoteId,
        targetPersonId=targetPersonId, targetCompanyId=targetCompanyId,
        targetOpportunityId=targetOpportunityId, targetDashboardId=targetDashboardId,
        targetWorkflowId=targetWorkflowId,
    )
    payload = _build_payload(params)
    return await get_client().update_attachments(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_attachment_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete an attachment by its ID (hard destroy).

    Args:
        id: The unique ID of the attachment to delete.
    """
    await get_client().delete_attachment_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_attachments(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete attachments by IDs (hard destroy).

    Args:
        ids: List of attachment IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_attachments(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# NoteTarget Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_note_targets(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all note target records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_note_targets(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_note_target_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single note target by its ID.

    Args:
        id: The unique ID of the note target.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_note_target_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def create_note_target(
    noteId: str,
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


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        id: The unique ID of the note target to update.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        ids: List of note target IDs (UUID format, e.g. "a1b2c3d4-..") to update.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_note_target_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a note target by its ID (hard destroy).

    Args:
        id: The unique ID of the note target to delete.
    """
    await get_client().delete_note_target_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_note_targets(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete note targets by IDs (hard destroy).

    Args:
        ids: List of note target IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_note_targets(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# TaskTarget Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_task_targets(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all task target records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_task_targets(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_task_target_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single task target by its ID.

    Args:
        id: The unique ID of the task target.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_task_target_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def create_task_target(
    taskId: str,
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


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        id: The unique ID of the task target to update.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        ids: List of task target IDs (UUID format, e.g. "a1b2c3d4-..") to update.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_task_target_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a task target by its ID (hard destroy).

    Args:
        id: The unique ID of the task target to delete.
    """
    await get_client().delete_task_target_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_task_targets(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete task targets by IDs (hard destroy).

    Args:
        ids: List of task target IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_task_targets(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# TimelineActivity Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_timeline_activities(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all timeline activity records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_timeline_activities(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_timeline_activity_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single timeline activity by its ID.

    Args:
        id: The unique ID of the timeline activity.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_timeline_activity_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        name: Name of the activity.
        happensAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        targetCompanyId: ID of the associated company.
        linkedRecordId: ID of a linked record (e.g. calendar event).
        linkedObjectMetadataId: Metadata ID for the linked record type.
        workspaceMemberId: ID of the workspace member who performed the activity.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
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
    properties: Optional[PropertiesModel] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing timeline activity record.

    Args:
        id: The unique ID of the timeline activity to update.
        name: Updated name of the activity.
        happensAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
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
        properties: Properties payload with before/after states and field diffs.
        position: Display position (0 to 1000000). Lower values appear first.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
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
    properties: Optional[PropertiesModel] = None,
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update timeline activity records by IDs.

    Args:
        ids: List of timeline activity IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        name: Updated name of the activity.
        happensAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
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
        properties: Properties payload with before/after states and field diffs.
        position: Display position (0 to 1000000). Lower values appear first.
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


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_timeline_activity_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a timeline activity by its ID (hard destroy).

    Args:
        id: The unique ID of the timeline activity to delete.
    """
    await get_client().delete_timeline_activity_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_timeline_activities(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete timeline activities by IDs (hard destroy).

    Args:
        ids: List of timeline activity IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_timeline_activities(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# CalendarEvent Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_calendar_events(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all calendar event records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_calendar_events(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_calendar_event_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single calendar event by its ID.

    Args:
        id: The unique ID of the calendar event.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_calendar_event_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
        title: Title of the calendar event.
        startsAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        endsAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        description: Description of the event.
        location: Event location as plain text.
        conferenceLink: Conference link with primaryLinkUrl and optional primaryLinkLabel.
    """
    params = CreateCalendarEventParam(
        title=title, startsAt=startsAt, endsAt=endsAt, description=description,
        location=location, conferenceLink=conferenceLink,
    )
    payload = _build_payload(params)
    return await get_client().create_calendar_event(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing calendar event record.

    Args:
        id: The unique ID of the calendar event to update.
        title: Updated title of the calendar event.
        description: Updated description.
        startsAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        endsAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        isCanceled: true or false
        isFullDay: true or false
        location: Updated event location as plain text.
        conferenceLink: Updated conference link with primaryLinkUrl and optional primaryLinkLabel.
        iCalUid: Updated iCal UID.
        position: Display position (0 to 1000000). Lower values appear first.
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


@mcp.tool(tags={"write", "primary", "twenty"})
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
    position: Optional[float] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update calendar event records by IDs.

    Args:
        ids: List of calendar event IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        title: Updated title of the calendar event.
        description: Updated description.
        startsAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        endsAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        isCanceled: true or false
        isFullDay: true or false
        location: Updated event location as plain text.
        conferenceLink: Updated conference link with primaryLinkUrl and optional primaryLinkLabel.
        iCalUid: Updated iCal UID.
        position: Display position (0 to 1000000). Lower values appear first.
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


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_calendar_event_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a calendar event by its ID (hard destroy).

    Args:
        id: The unique ID of the calendar event to delete.
    """
    await get_client().delete_calendar_event_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_calendar_events(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete calendar events by IDs (hard destroy).

    Args:
        ids: List of calendar event IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_calendar_events(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# CalendarEventParticipant Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_calendar_event_participants(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all calendar event participant records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_calendar_event_participants(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_calendar_event_participant_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single calendar event participant by its ID.

    Args:
        id: The unique ID of the calendar event participant.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_calendar_event_participant_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def create_calendar_event_participant(
    calendarEventId: str,
    handle: str,
    displayName: str,
    isOrganizer: bool = False,
    responseStatus: str = "needs_action",
    personId: str = "",
    workspaceMemberId: str = "",
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new calendar event participant record.

    Args:
        calendarEventId: ID of the associated calendar event.
        handle: Email handle of the participant.
        displayName: Display name of the participant.
        isOrganizer: true or false
        responseStatus: needs_action, declined, tentative, or accepted
        personId: ID of the associated person.
        workspaceMemberId: ID of the associated workspace member.
    """
    params = CreateCalendarEventParticipantParam(
        calendarEventId=calendarEventId, handle=handle, displayName=displayName,
        isOrganizer=isOrganizer, responseStatus=_enum_upper(responseStatus),
        personId=personId, workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().create_calendar_event_participant(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        id: The unique ID of the calendar event participant to update.
        calendarEventId: Updated associated calendar event ID.
        handle: Updated email handle.
        displayName: Updated display name.
        isOrganizer: true or false
        responseStatus: needs_action, declined, tentative, or accepted
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
    """
    params = UpdateCalendarEventParticipantParam(
        id=id, calendarEventId=calendarEventId, handle=handle, displayName=displayName,
        isOrganizer=isOrganizer, responseStatus=_enum_upper(responseStatus),
        personId=personId, workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_event_participant(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        ids: List of calendar event participant IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        calendarEventId: Updated associated calendar event ID.
        handle: Updated email handle.
        displayName: Updated display name.
        isOrganizer: true or false
        responseStatus: needs_action, declined, tentative, or accepted
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
    """
    params = UpdateCalendarEventParticipantParam(
        calendarEventId=calendarEventId, handle=handle, displayName=displayName,
        isOrganizer=isOrganizer, responseStatus=_enum_upper(responseStatus),
        personId=personId, workspaceMemberId=workspaceMemberId,
    )
    payload = _build_payload(params)
    return await get_client().update_calendar_event_participants(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_calendar_event_participant_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a calendar event participant by its ID (hard destroy).

    Args:
        id: The unique ID of the calendar event participant to delete.
    """
    await get_client().delete_calendar_event_participant_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_calendar_event_participants(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete calendar event participants by IDs (hard destroy).

    Args:
        ids: List of calendar event participant IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_calendar_event_participants(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Message Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_messages(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all message records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_messages(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_message_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single message by its ID.

    Args:
        id: The unique ID of the message.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_message_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def create_message(
    subject: str,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new message record.

    Args:
        subject: Subject of the message.
    """
    params = CreateMessageParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().create_message(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
        id: The unique ID of the message to update.
        headerMessageId: Updated header message ID.
        subject: Updated subject of the message.
        text: Updated body text of the message.
        receivedAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        messageThreadId: Updated associated message thread ID.
        messageCampaignId: Updated associated message campaign ID.
        deliveryStatus: queued, sent, failed, bounced, complained, or skipped
    """
    params = UpdateMessageParam(
        id=id, headerMessageId=headerMessageId, subject=subject, text=text,
        receivedAt=receivedAt, messageThreadId=messageThreadId,
        messageCampaignId=messageCampaignId, deliveryStatus=_enum_upper(deliveryStatus),
    )
    payload = _build_payload(params)
    return await get_client().update_message(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
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
        ids: List of message IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        headerMessageId: Updated header message ID.
        subject: Updated subject of the message.
        text: Updated body text of the message.
        receivedAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        messageThreadId: Updated associated message thread ID.
        messageCampaignId: Updated associated message campaign ID.
        deliveryStatus: queued, sent, failed, bounced, complained, or skipped
    """
    params = UpdateMessageParam(
        headerMessageId=headerMessageId, subject=subject, text=text,
        receivedAt=receivedAt, messageThreadId=messageThreadId,
        messageCampaignId=messageCampaignId, deliveryStatus=_enum_upper(deliveryStatus),
    )
    payload = _build_payload(params)
    return await get_client().update_messages(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_message_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a message by its ID (hard destroy).

    Args:
        id: The unique ID of the message to delete.
    """
    await get_client().delete_message_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_messages(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete messages by IDs (hard destroy).

    Args:
        ids: List of message IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_messages(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# MessageThread Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_message_threads(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all message thread records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_message_threads(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_message_thread_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single message thread by its ID.

    Args:
        id: The unique ID of the message thread.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_message_thread_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def create_message_thread(
    subject: str,
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


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_message_thread(
    id: str,
    subject: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Update an existing message thread record.

    Args:
        id: The unique ID of the message thread to update.
        subject: Updated subject of the message thread.
    """
    params = UpdateMessageThreadParam(id=id, subject=subject)
    payload = _build_payload(params)
    return await get_client().update_message_thread(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def update_message_threads(
    ids: list[str],
    subject: Optional[str] = None,
    ctx: Context = None
) -> dict[str, Any]:
    """Bulk update message thread records by IDs.

    Args:
        ids: List of message thread IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        subject: Updated subject of the message thread.
    """
    params = UpdateMessageThreadParam(subject=subject)
    payload = _build_payload(params)
    return await get_client().update_message_threads(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_message_thread_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a message thread by its ID (hard destroy).

    Args:
        id: The unique ID of the message thread to delete.
    """
    await get_client().delete_message_thread_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "primary", "twenty"})
async def delete_message_threads(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete message threads by IDs (hard destroy).

    Args:
        ids: List of message thread IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_message_threads(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# MessageParticipant Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_message_participants(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all message participant records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_message_participants(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_message_participant_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single message participant by its ID.

    Args:
        id: The unique ID of the message participant.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_message_participant_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        messageId: ID of the associated message.
        role: from, to, cc, or bcc
        handle: Email handle of the participant.
        displayName: Display name of the participant.
        personId: ID of the associated person.
        workspaceMemberId: ID of the associated workspace member.
        messageCampaignId: ID of the associated message campaign.
    """
    params = CreateMessageParticipantParam(
        messageId=messageId, role=_enum_upper(role), handle=handle, displayName=displayName,
        personId=personId, workspaceMemberId=workspaceMemberId,
        messageCampaignId=messageCampaignId,
    )
    payload = _build_payload(params)
    return await get_client().create_message_participant(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        id: The unique ID of the message participant to update.
        messageId: Updated associated message ID.
        role: from, to, cc, or bcc
        handle: Updated email handle.
        displayName: Updated display name.
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
        messageCampaignId: Updated associated message campaign ID.
    """
    params = UpdateMessageParticipantParam(
        id=id, messageId=messageId, role=_enum_upper(role), handle=handle, displayName=displayName,
        personId=personId, workspaceMemberId=workspaceMemberId,
        messageCampaignId=messageCampaignId,
    )
    payload = _build_payload(params)
    return await get_client().update_message_participant(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        ids: List of message participant IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        messageId: Updated associated message ID.
        role: from, to, cc, or bcc
        handle: Updated email handle.
        displayName: Updated display name.
        personId: Updated associated person ID.
        workspaceMemberId: Updated associated workspace member ID.
        messageCampaignId: Updated associated message campaign ID.
    """
    params = UpdateMessageParticipantParam(
        messageId=messageId, role=_enum_upper(role), handle=handle, displayName=displayName,
        personId=personId, workspaceMemberId=workspaceMemberId,
        messageCampaignId=messageCampaignId,
    )
    payload = _build_payload(params)
    return await get_client().update_message_participants(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_message_participant_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a message participant by its ID (hard destroy).

    Args:
        id: The unique ID of the message participant to delete.
    """
    await get_client().delete_message_participant_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_message_participants(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete message participants by IDs (hard destroy).

    Args:
        ids: List of message participant IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_message_participants(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# CallRecording Tools
# =============================================================================
@mcp.tool(tags={"read", "primary", "twenty"})
async def list_call_recordings(include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """List all call recording records.

    Args:
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    data = await get_client().get_all_call_recordings(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}


@mcp.tool(tags={"read", "primary", "twenty"})
async def get_call_recording_by_id(id: str, include_all_fields: bool = False, ctx: Context = None) -> dict[str, Any]:
    """Get a single call recording by its ID.

    Args:
        id: The unique ID of the call recording.
        include_all_fields: Default False (common fields only). Set True for all fields.
    """
    return await get_client().get_call_recording_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def create_call_recording(
    title: str,
    status: str,
    ctx: Context = None
) -> dict[str, Any]:
    """Create a new call recording record.

    Args:
        title: Title of the call recording.
        status: scheduled, joining, recording, processing, completed, or failed
    """
    params = CreateCallRecordingParam(title=title, status=_enum_upper(status))
    payload = _build_payload(params)
    return await get_client().create_call_recording(
        payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        id: The unique ID of the call recording to update.
        title: Updated title of the call recording.
        status: scheduled, joining, recording, processing, completed, or failed
        recordingRequestStatus: requested or canceled
        applicationId: Updated application ID.
        externalBotId: Updated external bot ID.
        externalRecordingId: Updated external recording ID.
        startedAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        endedAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        calendarEventId: Updated associated calendar event ID.
    """
    params = UpdateCallRecordingParam(
        id=id, title=title, status=_enum_upper(status), recordingRequestStatus=_enum_upper(recordingRequestStatus),
        applicationId=applicationId, externalBotId=externalBotId,
        externalRecordingId=externalRecordingId, startedAt=startedAt,
        endedAt=endedAt, calendarEventId=calendarEventId,
    )
    payload = _build_payload(params)
    return await get_client().update_call_recording(
        id, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
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
        ids: List of call recording IDs (UUID format, e.g. "a1b2c3d4-..") to update.
        title: Updated title of the call recording.
        status: scheduled, joining, recording, processing, completed, or failed
        recordingRequestStatus: requested or canceled
        applicationId: Updated application ID.
        externalBotId: Updated external bot ID.
        externalRecordingId: Updated external recording ID.
        startedAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        endedAt: ISO 8601 format (2026-06-22T15:00:00-04:00).
        calendarEventId: Updated associated calendar event ID.
    """
    params = UpdateCallRecordingParam(
        title=title, status=_enum_upper(status), recordingRequestStatus=_enum_upper(recordingRequestStatus),
        applicationId=applicationId, externalBotId=externalBotId,
        externalRecordingId=externalRecordingId, startedAt=startedAt,
        endedAt=endedAt, calendarEventId=calendarEventId,
    )
    payload = _build_payload(params)
    return await get_client().update_call_recordings(
        ids, payload, get_user_token(), include_all_fields=ALLOW_ALL_AGGREGATE
    )


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_call_recording_by_id(id: str, ctx: Context = None) -> dict[str, Any]:
    """Delete a call recording by its ID (hard destroy).

    Args:
        id: The unique ID of the call recording to delete.
    """
    await get_client().delete_call_recording_by_id(id, get_user_token())
    return {"deleted": True, "id": id}


@mcp.tool(tags={"write", "advanced", "twenty"})
async def delete_call_recordings(ids: list[str], ctx: Context = None) -> dict[str, Any]:
    """Bulk delete call recordings by IDs (hard destroy).

    Args:
        ids: List of call recording IDs (UUID format, e.g. "a1b2c3d4-..") to delete.
    """
    await get_client().delete_call_recordings(ids, get_user_token())
    return {"deleted": True, "count": len(ids)}


# =============================================================================
# Server Status Tool
# =============================================================================
@mcp.tool(tags={"read", "advanced", "twenty"})
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