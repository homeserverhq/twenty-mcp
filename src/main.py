import os
import sys
from contextvars import ContextVar
from typing import Any, Optional

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from toon_mcp import json_to_toon

from .client import TwentyClient

_current_user_token: ContextVar[Optional[str]] = ContextVar(
    "current_user_token", default=None
)

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

mcp = FastMCP("twenty-mcp")

_client: Optional[TwentyClient] = None

def get_client() -> TwentyClient:
    global _client
    if _client is None:
        _client = TwentyClient()
    return _client

def get_user_token() -> Optional[str]:
    return _current_user_token.get()

ALLOW_ALL_AGGREGATE = os.getenv("ALLOW_ALL_AGGREGATE", "false").lower() in ("true", "1", "yes")

# =============================================================================
# Pydantic Contract Models
# =============================================================================

class DomainNameInput(BaseModel):
    primaryLinkUrl: str = ""
    primaryLinkLabel: str = ""
    secondaryLinks: list = Field(default_factory=list)

class CurrencyInput(BaseModel):
    amountMicros: Optional[int] = None
    currencyCode: Optional[str] = None

class AddressInput(BaseModel):
    addressStreet1: str = ""
    addressStreet2: str = ""
    addressCity: str = ""
    addressPostcode: str = ""
    addressState: str = ""
    addressCountry: str = ""
    addressLat: Optional[float] = None
    addressLng: Optional[float] = None

class FullNameInput(BaseModel):
    firstName: str = ""
    lastName: str = ""

class EmailsInput(BaseModel):
    primaryEmail: str = ""
    additionalEmails: list = Field(default_factory=list)

class PhonesInput(BaseModel):
    primaryPhoneNumber: str = ""
    primaryPhoneCountryCode: str = ""
    primaryPhoneCallingCode: str = ""
    additionalPhones: list = Field(default_factory=list)

class BodyV2Input(BaseModel):
    blocknote: Optional[Any] = None
    markdown: str = ""

# =============================================================================
# Company Tools
# =============================================================================

@mcp.tool()
async def get_all_companies(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all company records.

    Args:
        include_all_fields: When False (default), each company contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_companies(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_company_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single company by ID.

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
    domainName: Optional[dict[str, Any]] = None,
    companyType: Optional[str] = None,
    industry: Optional[str] = None,
    description: Optional[str] = "",
    employees: Optional[int] = 0,
    linkedinUrl: Optional[str] = "",
    annualRecurringRevenue: Optional[dict[str, Any]] = None,
    address: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new company.

    Args:
        name: Name of the company (required).
        domainName: Nested domain name object with primaryLinkUrl, primaryLinkLabel, secondaryLinks.
        companyType: Type of company (e.g. COMPANY, INDIVIDUAL).
        industry: Industry sector.
        description: Company description.
        employees: Number of employees.
        linkedinUrl: LinkedIn profile URL.
        annualRecurringRevenue: Nested currency object {amountMicros, currencyCode}.
        address: Nested address object with street, city, postcode, state, country fields.
    """
    return await get_client().create_company(
        get_user_token(), name, domainName, companyType, industry,
        description, employees, linkedinUrl, annualRecurringRevenue, address,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_company(
    id: str,
    name: Optional[str] = None,
    domainName: Optional[dict[str, Any]] = None,
    companyType: Optional[str] = None,
    industry: Optional[str] = None,
    description: Optional[str] = None,
    employees: Optional[int] = None,
    linkedinUrl: Optional[str] = None,
    annualRecurringRevenue: Optional[dict[str, Any]] = None,
    address: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing company.

    Args:
        id: The unique ID of the company to update (required).
        name: Name of the company.
        domainName: Nested domain name object.
        companyType: Type of company.
        industry: Industry sector.
        description: Company description.
        employees: Number of employees.
        linkedinUrl: LinkedIn profile URL.
        annualRecurringRevenue: Nested currency object.
        address: Nested address object.
    """
    return await get_client().update_company(
        id, get_user_token(), name, domainName, companyType, industry,
        description, employees, linkedinUrl, annualRecurringRevenue, address,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_companies(
    filter_id_in: Optional[list[str]] = None,
    name: Optional[str] = None,
    companyType: Optional[str] = None,
    industry: Optional[str] = None,
    description: Optional[str] = None,
    employees: Optional[int] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update companies matching a filter.

    Args:
        filter_id_in: List of company IDs to update (required for bulk update).
        name: New name value.
        companyType: New companyType value.
        industry: New industry value.
        description: New description value.
        employees: New employee count.
    """
    items = await get_client().update_many_companies(
        get_user_token(), filter_id_in, name, companyType, industry, description, employees,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_company_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a company by ID.

    Args:
        id: The unique ID of the company to delete (required).
    """
    return await get_client().delete_company_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_companies(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete companies matching a filter.

    Args:
        filter_id_in: List of company IDs to delete (required for bulk delete).
    """
    items = await get_client().delete_many_companies(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Person Tools
# =============================================================================

@mcp.tool()
async def get_all_people(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all person records.

    Args:
        include_all_fields: When False (default), each person contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_people(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_person_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single person by ID.

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
    name: dict[str, Any],
    emails: dict[str, Any],
    firstName: Optional[str] = "",
    lastName: Optional[str] = "",
    jobTitle: Optional[str] = "",
    linkedinUrl: Optional[str] = "",
    phones: Optional[dict[str, Any]] = None,
    city: Optional[str] = "",
    companyId: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new person.

    Args:
        name: Nested name object with firstName and lastName (required).
        emails: Nested emails object with primaryEmail (required).
        firstName: First name (use instead of name dict for simple cases).
        lastName: Last name (use instead of name dict for simple cases).
        jobTitle: Job title.
        linkedinUrl: LinkedIn profile URL.
        phones: Nested phones object.
        city: City location.
        companyId: ID of associated company.
    """
    return await get_client().create_person(
        get_user_token(), name, emails, firstName, lastName, jobTitle,
        linkedinUrl, phones, city, companyId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_person(
    id: str,
    name: Optional[dict[str, Any]] = None,
    emails: Optional[dict[str, Any]] = None,
    jobTitle: Optional[str] = None,
    phones: Optional[dict[str, Any]] = None,
    city: Optional[str] = None,
    companyId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing person.

    Args:
        id: The unique ID of the person to update (required).
        name: Nested name object.
        emails: Nested emails object.
        jobTitle: New job title.
        phones: Nested phones object.
        city: New city.
        companyId: New company association.
    """
    return await get_client().update_person(
        id, get_user_token(), name, emails, jobTitle, phones, city, companyId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_people(
    filter_id_in: Optional[list[str]] = None,
    jobTitle: Optional[str] = None,
    city: Optional[str] = None,
    companyId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update people matching a filter.

    Args:
        filter_id_in: List of person IDs to update.
        jobTitle: New job title value.
        city: New city value.
        companyId: New company ID.
    """
    items = await get_client().update_many_people(
        get_user_token(), filter_id_in, jobTitle, city, companyId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_person_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a person by ID.

    Args:
        id: The unique ID of the person to delete (required).
    """
    return await get_client().delete_person_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_people(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete people matching a filter.

    Args:
        filter_id_in: List of person IDs to delete.
    """
    items = await get_client().delete_many_people(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Opportunity Tools
# =============================================================================

@mcp.tool()
async def get_all_opportunities(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all opportunity records.

    Args:
        include_all_fields: When False (default), each opportunity contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_opportunities(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_opportunity_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single opportunity by ID.

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
    amount: Optional[dict[str, Any]] = None,
    probability: Optional[int] = None,
    closeDate: Optional[str] = None,
    companyId: Optional[str] = None,
    personId: Optional[str] = None,
    description: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new opportunity.

    Args:
        name: Name of the opportunity (required).
        stage: Sales stage e.g. NEW, SCREENING, MEETING, PROPOSAL, CUSTOMER (required).
        amount: Nested currency object with amountMicros and currencyCode.
        probability: Probability percentage (0-100).
        closeDate: Expected close date in ISO 8601 format with UTC offset.
        companyId: ID of associated company.
        personId: ID of associated person (point of contact).
        description: Opportunity description.
    """
    return await get_client().create_opportunity(
        get_user_token(), name, stage, amount, probability, closeDate,
        companyId, personId, description,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_opportunity(
    id: str,
    name: Optional[str] = None,
    stage: Optional[str] = None,
    amount: Optional[dict[str, Any]] = None,
    probability: Optional[int] = None,
    closeDate: Optional[str] = None,
    companyId: Optional[str] = None,
    personId: Optional[str] = None,
    description: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing opportunity.

    Args:
        id: The unique ID of the opportunity to update (required).
        name: New name.
        stage: New sales stage.
        amount: Nested currency object.
        probability: New probability percentage.
        closeDate: New close date in ISO 8601 format with UTC offset.
        companyId: New company association.
        personId: New person association.
        description: New description.
    """
    return await get_client().update_opportunity(
        id, get_user_token(), name, stage, amount, probability, closeDate,
        companyId, personId, description,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_opportunities(
    filter_id_in: Optional[list[str]] = None,
    stage: Optional[str] = None,
    probability: Optional[int] = None,
    companyId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update opportunities matching a filter.

    Args:
        filter_id_in: List of opportunity IDs to update.
        stage: New stage value.
        probability: New probability value.
        companyId: New company ID.
    """
    items = await get_client().update_many_opportunities(
        get_user_token(), filter_id_in, stage, probability, companyId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_opportunity_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete an opportunity by ID.

    Args:
        id: The unique ID of the opportunity to delete (required).
    """
    return await get_client().delete_opportunity_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_opportunities(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete opportunities matching a filter.

    Args:
        filter_id_in: List of opportunity IDs to delete.
    """
    items = await get_client().delete_many_opportunities(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Task Tools
# =============================================================================

@mcp.tool()
async def get_all_tasks(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all task records.

    Args:
        include_all_fields: When False (default), each task contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_tasks(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_task_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single task by ID.

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
    dueAt: Optional[str] = None,
    bodyV2: Optional[dict[str, Any]] = None,
    assigneeId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new task.

    Args:
        title: Title of the task (required).
        status: Status e.g. TODO, IN_PROGRESS, COMPLETED (required).
        dueAt: Due date in ISO 8601 format with explicit UTC offset.
        bodyV2: Nested body content object with blocknote and markdown.
        assigneeId: ID of the assigned workspace member.
    """
    return await get_client().create_task(
        get_user_token(), title, status, dueAt, bodyV2, assigneeId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_task(
    id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    dueAt: Optional[str] = None,
    bodyV2: Optional[dict[str, Any]] = None,
    assigneeId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing task.

    Args:
        id: The unique ID of the task to update (required).
        title: New title.
        status: New status.
        dueAt: New due date in ISO 8601 format with explicit UTC offset.
        bodyV2: New body content object.
        assigneeId: New assignee ID.
    """
    return await get_client().update_task(
        id, get_user_token(), title, status, dueAt, bodyV2, assigneeId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_tasks(
    filter_id_in: Optional[list[str]] = None,
    status: Optional[str] = None,
    assigneeId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update tasks matching a filter.

    Args:
        filter_id_in: List of task IDs to update.
        status: New status value.
        assigneeId: New assignee ID.
    """
    items = await get_client().update_many_tasks(
        get_user_token(), filter_id_in, status, assigneeId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_task_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a task by ID.

    Args:
        id: The unique ID of the task to delete (required).
    """
    return await get_client().delete_task_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_tasks(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete tasks matching a filter.

    Args:
        filter_id_in: List of task IDs to delete.
    """
    items = await get_client().delete_many_tasks(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Note Tools
# =============================================================================

@mcp.tool()
async def get_all_notes(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all note records.

    Args:
        include_all_fields: When False (default), each note contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_notes(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_note_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single note by ID.

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
    bodyV2: Optional[dict[str, Any]] = None,
    authorId: Optional[str] = None,
    pinned: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new note.

    Args:
        title: Title of the note (required).
        bodyV2: Nested body object with blocknote and markdown fields.
        authorId: ID of the author.
        pinned: Whether the note is pinned.
    """
    return await get_client().create_note(
        get_user_token(), title, bodyV2, authorId, pinned,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_note(
    id: str,
    title: Optional[str] = None,
    bodyV2: Optional[dict[str, Any]] = None,
    pinned: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing note.

    Args:
        id: The unique ID of the note to update (required).
        title: New title.
        bodyV2: New body object.
        pinned: New pinned state.
    """
    return await get_client().update_note(
        id, get_user_token(), title, bodyV2, pinned,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_notes(
    filter_id_in: Optional[list[str]] = None,
    pinned: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update notes matching a filter.

    Args:
        filter_id_in: List of note IDs to update.
        pinned: New pinned state.
    """
    items = await get_client().update_many_notes(
        get_user_token(), filter_id_in, pinned,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_note_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a note by ID.

    Args:
        id: The unique ID of the note to delete (required).
    """
    return await get_client().delete_note_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_notes(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete notes matching a filter.

    Args:
        filter_id_in: List of note IDs to delete.
    """
    items = await get_client().delete_many_notes(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Attachment Tools
# =============================================================================

@mcp.tool()
async def get_all_attachments(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all attachment records.

    Args:
        include_all_fields: When False (default), each attachment contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_attachments(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_attachment_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single attachment by ID.

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
    fullPath: str,
    type: Optional[str] = "",
    fileCategory: Optional[str] = None,
    authorId: Optional[str] = "",
    taskId: Optional[str] = "",
    noteId: Optional[str] = "",
    personId: Optional[str] = "",
    companyId: Optional[str] = "",
    opportunityId: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new attachment.

    Args:
        name: Name of the attachment (required).
        fullPath: Full file path (required).
        type: Attachment type.
        fileCategory: File category.
        authorId: ID of the author.
        taskId: ID of associated task.
        noteId: ID of associated note.
        personId: ID of associated person.
        companyId: ID of associated company.
        opportunityId: ID of associated opportunity.
    """
    return await get_client().create_attachment(
        get_user_token(), name, fullPath, type, fileCategory, authorId,
        taskId, noteId, personId, companyId, opportunityId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_attachment(
    id: str,
    name: Optional[str] = None,
    fullPath: Optional[str] = None,
    type: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing attachment.

    Args:
        id: The unique ID of the attachment to update (required).
        name: New name.
        fullPath: New full path.
        type: New type.
    """
    return await get_client().update_attachment(
        id, get_user_token(), name, fullPath, type,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_attachments(
    filter_id_in: Optional[list[str]] = None,
    name: Optional[str] = None,
    type: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update attachments matching a filter.

    Args:
        filter_id_in: List of attachment IDs to update.
        name: New name value.
        type: New type value.
    """
    items = await get_client().update_many_attachments(
        get_user_token(), filter_id_in, name, type,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_attachment_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete an attachment by ID.

    Args:
        id: The unique ID of the attachment to delete (required).
    """
    return await get_client().delete_attachment_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_attachments(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete attachments matching a filter.

    Args:
        filter_id_in: List of attachment IDs to delete.
    """
    items = await get_client().delete_many_attachments(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Favorite Tools
# =============================================================================

@mcp.tool()
async def get_all_favorites(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all favorite records.

    Args:
        include_all_fields: When False (default), each favorite contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_favorites(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_favorite_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single favorite by ID.

    Args:
        id: The unique ID of the favorite (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_favorite_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_favorite(
    viewId: str,
    companyId: Optional[str] = "",
    personId: Optional[str] = "",
    taskId: Optional[str] = "",
    noteId: Optional[str] = "",
    opportunityId: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new favorite.

    Args:
        viewId: ID of the view (required).
        companyId: ID of associated company.
        personId: ID of associated person.
        taskId: ID of associated task.
        noteId: ID of associated note.
        opportunityId: ID of associated opportunity.
    """
    return await get_client().create_favorite(
        get_user_token(), viewId, companyId, personId, taskId, noteId, opportunityId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_favorite(
    id: str,
    viewId: Optional[str] = None,
    companyId: Optional[str] = None,
    personId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing favorite.

    Args:
        id: The unique ID of the favorite to update (required).
        viewId: New view ID.
        companyId: New company ID.
        personId: New person ID.
    """
    return await get_client().update_favorite(
        id, get_user_token(), viewId, companyId, personId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_favorites(
    filter_id_in: Optional[list[str]] = None,
    viewId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update favorites matching a filter.

    Args:
        filter_id_in: List of favorite IDs to update.
        viewId: New view ID.
    """
    items = await get_client().update_many_favorites(
        get_user_token(), filter_id_in, viewId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_favorite_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a favorite by ID.

    Args:
        id: The unique ID of the favorite to delete (required).
    """
    return await get_client().delete_favorite_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_favorites(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete favorites matching a filter.

    Args:
        filter_id_in: List of favorite IDs to delete.
    """
    items = await get_client().delete_many_favorites(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Workflow Tools
# =============================================================================

@mcp.tool()
async def get_all_workflows(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all workflow records.

    Args:
        include_all_fields: When False (default), each workflow contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workflows(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_workflow_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single workflow by ID.

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
    statuses: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new workflow.

    Args:
        name: Name of the workflow (required).
        statuses: List of status values (e.g. ["ACTIVE"]).
    """
    return await get_client().create_workflow(
        get_user_token(), name, statuses,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_workflow(
    id: str,
    name: Optional[str] = None,
    statuses: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing workflow.

    Args:
        id: The unique ID of the workflow to update (required).
        name: New name.
        statuses: New list of status values.
    """
    return await get_client().update_workflow(
        id, get_user_token(), name, statuses,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_workflows(
    filter_id_in: Optional[list[str]] = None,
    statuses: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update workflows matching a filter.

    Args:
        filter_id_in: List of workflow IDs to update.
        statuses: New status values.
    """
    items = await get_client().update_many_workflows(
        get_user_token(), filter_id_in, statuses,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_workflow_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a workflow by ID.

    Args:
        id: The unique ID of the workflow to delete (required).
    """
    return await get_client().delete_workflow_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_workflows(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete workflows matching a filter.

    Args:
        filter_id_in: List of workflow IDs to delete.
    """
    items = await get_client().delete_many_workflows(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# WorkflowVersion Tools
# =============================================================================

@mcp.tool()
async def get_all_workflowVersions(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all workflow version records.

    Args:
        include_all_fields: When False (default), each version contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workflowVersions(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_workflowVersion_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single workflow version by ID.

    Args:
        id: The unique ID of the workflow version (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_workflowVersion_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_workflowVersion(
    workflowId: str,
    name: Optional[str] = "",
    trigger: Optional[dict[str, Any]] = None,
    steps: Optional[list[Any]] = None,
    status: Optional[str] = "DRAFT",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new workflow version.

    Args:
        workflowId: ID of the parent workflow (required).
        name: Name of the version.
        trigger: Nested trigger object with name, type, settings.
        steps: List of step objects.
        status: Status e.g. DRAFT, ACTIVE.
    """
    return await get_client().create_workflowVersion(
        get_user_token(), workflowId, name, trigger, steps, status,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_workflowVersion(
    id: str,
    name: Optional[str] = None,
    trigger: Optional[dict[str, Any]] = None,
    steps: Optional[list[Any]] = None,
    status: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing workflow version.

    Args:
        id: The unique ID of the workflow version to update (required).
        name: New name.
        trigger: New trigger object.
        steps: New steps list.
        status: New status.
    """
    return await get_client().update_workflowVersion(
        id, get_user_token(), name, trigger, steps, status,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_workflowVersions(
    filter_id_in: Optional[list[str]] = None,
    status: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update workflow versions matching a filter.

    Args:
        filter_id_in: List of workflow version IDs to update.
        status: New status value.
    """
    items = await get_client().update_many_workflowVersions(
        get_user_token(), filter_id_in, status,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_workflowVersion_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a workflow version by ID.

    Args:
        id: The unique ID of the workflow version to delete (required).
    """
    return await get_client().delete_workflowVersion_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_workflowVersions(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete workflow versions matching a filter.

    Args:
        filter_id_in: List of workflow version IDs to delete.
    """
    items = await get_client().delete_many_workflowVersions(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# WorkflowRun Tools
# =============================================================================

@mcp.tool()
async def get_all_workflowRuns(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all workflow run records.

    Args:
        include_all_fields: When False (default), each run contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workflowRuns(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_workflowRun_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single workflow run by ID.

    Args:
        id: The unique ID of the workflow run (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_workflowRun_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_workflowRun(
    workflowId: str,
    workflowVersionId: Optional[str] = "",
    status: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new workflow run.

    Args:
        workflowId: ID of the parent workflow (required).
        workflowVersionId: ID of the workflow version.
        status: Run status.
    """
    return await get_client().create_workflowRun(
        get_user_token(), workflowId, workflowVersionId, status,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_workflowRun(
    id: str,
    status: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing workflow run.

    Args:
        id: The unique ID of the workflow run to update (required).
        status: New status.
    """
    return await get_client().update_workflowRun(
        id, get_user_token(), status,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_workflowRuns(
    filter_id_in: Optional[list[str]] = None,
    status: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update workflow runs matching a filter.

    Args:
        filter_id_in: List of workflow run IDs to update.
        status: New status value.
    """
    items = await get_client().update_many_workflowRuns(
        get_user_token(), filter_id_in, status,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_workflowRun_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a workflow run by ID.

    Args:
        id: The unique ID of the workflow run to delete (required).
    """
    return await get_client().delete_workflowRun_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_workflowRuns(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete workflow runs matching a filter.

    Args:
        filter_id_in: List of workflow run IDs to delete.
    """
    items = await get_client().delete_many_workflowRuns(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# WorkflowAutomatedTrigger Tools
# =============================================================================

@mcp.tool()
async def get_all_workflowAutomatedTriggers(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all workflow automated trigger records.

    Args:
        include_all_fields: When False (default), each trigger contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workflowAutomatedTriggers(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_workflowAutomatedTrigger_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single workflow automated trigger by ID.

    Args:
        id: The unique ID of the trigger (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_workflowAutomatedTrigger_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_workflowAutomatedTrigger(
    type: str,
    workflowId: Optional[str] = "",
    settings: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new workflow automated trigger.

    Args:
        type: Trigger type e.g. DATABASE (required).
        workflowId: ID of the associated workflow.
        settings: Nested settings object.
    """
    return await get_client().create_workflowAutomatedTrigger(
        get_user_token(), type, workflowId, settings,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_workflowAutomatedTrigger(
    id: str,
    type: Optional[str] = None,
    settings: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing workflow automated trigger.

    Args:
        id: The unique ID of the trigger to update (required).
        type: New type.
        settings: New settings object.
    """
    return await get_client().update_workflowAutomatedTrigger(
        id, get_user_token(), type, settings,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_workflowAutomatedTriggers(
    filter_id_in: Optional[list[str]] = None,
    type: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update workflow automated triggers matching a filter.

    Args:
        filter_id_in: List of trigger IDs to update.
        type: New type value.
    """
    items = await get_client().update_many_workflowAutomatedTriggers(
        get_user_token(), filter_id_in, type,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_workflowAutomatedTrigger_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a workflow automated trigger by ID.

    Args:
        id: The unique ID of the trigger to delete (required).
    """
    return await get_client().delete_workflowAutomatedTrigger_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_workflowAutomatedTriggers(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete workflow automated triggers matching a filter.

    Args:
        filter_id_in: List of trigger IDs to delete.
    """
    items = await get_client().delete_many_workflowAutomatedTriggers(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# CalendarEvent Tools
# =============================================================================

@mcp.tool()
async def get_all_calendarEvents(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all calendar event records.

    Args:
        include_all_fields: When False (default), each event contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_calendarEvents(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_calendarEvent_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single calendar event by ID.

    Args:
        id: The unique ID of the calendar event (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_calendarEvent_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_calendarEvent(
    title: str,
    startsAt: Optional[str] = "",
    endsAt: Optional[str] = "",
    description: Optional[str] = "",
    location: Optional[str] = "",
    isFullDay: Optional[bool] = False,
    isCanceled: Optional[bool] = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new calendar event.

    Args:
        title: Title of the event (required).
        startsAt: Start time in ISO 8601 format with explicit UTC offset.
        endsAt: End time in ISO 8601 format with explicit UTC offset.
        description: Event description.
        location: Event location.
        isFullDay: Whether the event is all day.
        isCanceled: Whether the event is canceled.
    """
    return await get_client().create_calendarEvent(
        get_user_token(), title, startsAt, endsAt, description, location, isFullDay, isCanceled,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_calendarEvent(
    id: str,
    title: Optional[str] = None,
    startsAt: Optional[str] = None,
    endsAt: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    isFullDay: Optional[bool] = None,
    isCanceled: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing calendar event.

    Args:
        id: The unique ID of the calendar event to update (required).
        title: New title.
        startsAt: New start time in ISO 8601 format with explicit UTC offset.
        endsAt: New end time in ISO 8601 format with explicit UTC offset.
        description: New description.
        location: New location.
        isFullDay: New all-day flag.
        isCanceled: New canceled flag.
    """
    return await get_client().update_calendarEvent(
        id, get_user_token(), title, startsAt, endsAt, description, location, isFullDay, isCanceled,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_calendarEvents(
    filter_id_in: Optional[list[str]] = None,
    isCanceled: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update calendar events matching a filter.

    Args:
        filter_id_in: List of calendar event IDs to update.
        isCanceled: New canceled state.
    """
    items = await get_client().update_many_calendarEvents(
        get_user_token(), filter_id_in, isCanceled,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_calendarEvent_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a calendar event by ID.

    Args:
        id: The unique ID of the calendar event to delete (required).
    """
    return await get_client().delete_calendarEvent_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_calendarEvents(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete calendar events matching a filter.

    Args:
        filter_id_in: List of calendar event IDs to delete.
    """
    items = await get_client().delete_many_calendarEvents(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# CalendarChannel Tools
# =============================================================================

@mcp.tool()
async def get_all_calendarChannels(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all calendar channel records.

    Args:
        include_all_fields: When False (default), each channel contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_calendarChannels(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_calendarChannel_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single calendar channel by ID.

    Args:
        id: The unique ID of the calendar channel (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_calendarChannel_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_calendarChannel(
    handle: Optional[str] = "",
    type: Optional[str] = None,
    visibility: Optional[str] = "SHARE_EVERYTHING",
    isContactAutoCreationEnabled: Optional[bool] = True,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new calendar channel.

    Args:
        handle: Email handle/address.
        type: Channel type.
        visibility: Visibility setting e.g. SHARE_EVERYTHING.
        isContactAutoCreationEnabled: Auto-create contacts from emails.
    """
    return await get_client().create_calendarChannel(
        get_user_token(), handle, type, visibility, isContactAutoCreationEnabled,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_calendarChannel(
    id: str,
    handle: Optional[str] = None,
    visibility: Optional[str] = None,
    isContactAutoCreationEnabled: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing calendar channel.

    Args:
        id: The unique ID of the calendar channel to update (required).
        handle: New handle.
        visibility: New visibility.
        isContactAutoCreationEnabled: New auto-create flag.
    """
    return await get_client().update_calendarChannel(
        id, get_user_token(), handle, visibility, isContactAutoCreationEnabled,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_calendarChannels(
    filter_id_in: Optional[list[str]] = None,
    visibility: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update calendar channels matching a filter.

    Args:
        filter_id_in: List of calendar channel IDs to update.
        visibility: New visibility value.
    """
    items = await get_client().update_many_calendarChannels(
        get_user_token(), filter_id_in, visibility,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_calendarChannel_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a calendar channel by ID.

    Args:
        id: The unique ID of the calendar channel to delete (required).
    """
    return await get_client().delete_calendarChannel_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_calendarChannels(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete calendar channels matching a filter.

    Args:
        filter_id_in: List of calendar channel IDs to delete.
    """
    items = await get_client().delete_many_calendarChannels(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# CalendarChannelEventAssociation Tools
# =============================================================================

@mcp.tool()
async def get_all_calendarChannelEventAssociations(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all calendar channel event association records.

    Args:
        include_all_fields: When False (default), each association contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_calendarChannelEventAssociations(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_calendarChannelEventAssociation_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single calendar channel event association by ID.

    Args:
        id: The unique ID of the association (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_calendarChannelEventAssociation_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_calendarChannelEventAssociation(
    calendarChannelId: str,
    calendarEventId: str,
    eventExternalId: Optional[str] = "",
    recurringEventExternalId: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new calendar channel event association.

    Args:
        calendarChannelId: ID of the calendar channel (required).
        calendarEventId: ID of the calendar event (required).
        eventExternalId: External event ID.
        recurringEventExternalId: Recurring external event ID.
    """
    return await get_client().create_calendarChannelEventAssociation(
        get_user_token(), calendarChannelId, calendarEventId, eventExternalId, recurringEventExternalId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_calendarChannelEventAssociation(
    id: str,
    eventExternalId: Optional[str] = None,
    recurringEventExternalId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing calendar channel event association.

    Args:
        id: The unique ID of the association to update (required).
        eventExternalId: New external event ID.
        recurringEventExternalId: New recurring external event ID.
    """
    return await get_client().update_calendarChannelEventAssociation(
        id, get_user_token(), eventExternalId, recurringEventExternalId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_calendarChannelEventAssociations(
    filter_id_in: Optional[list[str]] = None,
    eventExternalId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update calendar channel event associations matching a filter.

    Args:
        filter_id_in: List of association IDs to update.
        eventExternalId: New external event ID.
    """
    items = await get_client().update_many_calendarChannelEventAssociations(
        get_user_token(), filter_id_in, eventExternalId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_calendarChannelEventAssociation_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a calendar channel event association by ID.

    Args:
        id: The unique ID of the association to delete (required).
    """
    return await get_client().delete_calendarChannelEventAssociation_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_calendarChannelEventAssociations(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete calendar channel event associations matching a filter.

    Args:
        filter_id_in: List of association IDs to delete.
    """
    items = await get_client().delete_many_calendarChannelEventAssociations(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# CalendarEventParticipant Tools
# =============================================================================

@mcp.tool()
async def get_all_calendarEventParticipants(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all calendar event participant records.

    Args:
        include_all_fields: When False (default), each participant contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_calendarEventParticipants(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_calendarEventParticipant_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single calendar event participant by ID.

    Args:
        id: The unique ID of the participant (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_calendarEventParticipant_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_calendarEventParticipant(
    calendarEventId: str,
    handle: Optional[str] = "",
    displayName: Optional[str] = "",
    isOrganizer: Optional[bool] = False,
    responseStatus: Optional[str] = None,
    personId: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new calendar event participant.

    Args:
        calendarEventId: ID of the calendar event (required).
        handle: Email handle.
        displayName: Display name.
        isOrganizer: Whether this participant is the organizer.
        responseStatus: Response status.
        personId: ID of associated person.
    """
    return await get_client().create_calendarEventParticipant(
        get_user_token(), calendarEventId, handle, displayName, isOrganizer, responseStatus, personId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_calendarEventParticipant(
    id: str,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    isOrganizer: Optional[bool] = None,
    responseStatus: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing calendar event participant.

    Args:
        id: The unique ID of the participant to update (required).
        handle: New handle.
        displayName: New display name.
        isOrganizer: New organizer flag.
        responseStatus: New response status.
    """
    return await get_client().update_calendarEventParticipant(
        id, get_user_token(), handle, displayName, isOrganizer, responseStatus,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_calendarEventParticipants(
    filter_id_in: Optional[list[str]] = None,
    responseStatus: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update calendar event participants matching a filter.

    Args:
        filter_id_in: List of participant IDs to update.
        responseStatus: New response status.
    """
    items = await get_client().update_many_calendarEventParticipants(
        get_user_token(), filter_id_in, responseStatus,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_calendarEventParticipant_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a calendar event participant by ID.

    Args:
        id: The unique ID of the participant to delete (required).
    """
    return await get_client().delete_calendarEventParticipant_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_calendarEventParticipants(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete calendar event participants matching a filter.

    Args:
        filter_id_in: List of participant IDs to delete.
    """
    items = await get_client().delete_many_calendarEventParticipants(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Message Tools
# =============================================================================

@mcp.tool()
async def get_all_messages(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all message records.

    Args:
        include_all_fields: When False (default), each message contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messages(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_message_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single message by ID.

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
    text: Optional[str] = None,
    subject: Optional[str] = None,
    headerMessageId: Optional[str] = None,
    messageThreadId: Optional[str] = None,
    receivedAt: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new message.

    Args:
        text: Message body text.
        subject: Message subject.
        headerMessageId: Header message ID.
        messageThreadId: ID of the associated message thread.
        receivedAt: Received timestamp in ISO 8601 format with explicit UTC offset.
    """
    return await get_client().create_message(
        get_user_token(), text, subject, headerMessageId, messageThreadId, receivedAt,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_message(
    id: str,
    text: Optional[str] = None,
    subject: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing message.

    Args:
        id: The unique ID of the message to update (required).
        text: New message text.
        subject: New subject.
    """
    return await get_client().update_message(
        id, get_user_token(), text, subject,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_messages(
    filter_id_in: Optional[list[str]] = None,
    subject: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update messages matching a filter.

    Args:
        filter_id_in: List of message IDs to update.
        subject: New subject value.
    """
    items = await get_client().update_many_messages(
        get_user_token(), filter_id_in, subject,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_message_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a message by ID.

    Args:
        id: The unique ID of the message to delete (required).
    """
    return await get_client().delete_message_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_messages(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete messages matching a filter.

    Args:
        filter_id_in: List of message IDs to delete.
    """
    items = await get_client().delete_many_messages(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# MessageThread Tools
# =============================================================================

@mcp.tool()
async def get_all_messageThreads(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all message thread records.

    Args:
        include_all_fields: When False (default), each thread contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messageThreads(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_messageThread_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single message thread by ID.

    Args:
        id: The unique ID of the message thread (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_messageThread_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_messageThread(
    subject: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new message thread.

    Args:
        subject: Thread subject.
    """
    return await get_client().create_messageThread(
        get_user_token(), subject,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_messageThread(
    id: str,
    subject: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing message thread.

    Args:
        id: The unique ID of the message thread to update (required).
        subject: New subject.
    """
    return await get_client().update_messageThread(
        id, get_user_token(), subject,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_messageThreads(
    filter_id_in: Optional[list[str]] = None,
    subject: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update message threads matching a filter.

    Args:
        filter_id_in: List of thread IDs to update.
        subject: New subject value.
    """
    items = await get_client().update_many_messageThreads(
        get_user_token(), filter_id_in, subject,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_messageThread_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a message thread by ID.

    Args:
        id: The unique ID of the message thread to delete (required).
    """
    return await get_client().delete_messageThread_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_messageThreads(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete message threads matching a filter.

    Args:
        filter_id_in: List of thread IDs to delete.
    """
    items = await get_client().delete_many_messageThreads(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# MessageChannel Tools
# =============================================================================

@mcp.tool()
async def get_all_messageChannels(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all message channel records.

    Args:
        include_all_fields: When False (default), each channel contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messageChannels(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_messageChannel_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single message channel by ID.

    Args:
        id: The unique ID of the message channel (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_messageChannel_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_messageChannel(
    handle: Optional[str] = None,
    type: Optional[str] = None,
    visibility: Optional[str] = None,
    isContactAutoCreationEnabled: Optional[bool] = None,
    connectedAccountId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new message channel.

    Args:
        handle: Email handle/address.
        type: Channel type.
        visibility: Visibility setting.
        isContactAutoCreationEnabled: Auto-create contacts from emails.
        connectedAccountId: ID of the connected account.
    """
    return await get_client().create_messageChannel(
        get_user_token(), handle, type, visibility, isContactAutoCreationEnabled, connectedAccountId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_messageChannel(
    id: str,
    handle: Optional[str] = None,
    visibility: Optional[str] = None,
    isSyncEnabled: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing message channel.

    Args:
        id: The unique ID of the message channel to update (required).
        handle: New handle.
        visibility: New visibility.
        isSyncEnabled: New sync enabled flag.
    """
    return await get_client().update_messageChannel(
        id, get_user_token(), handle, visibility, isSyncEnabled,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_messageChannels(
    filter_id_in: Optional[list[str]] = None,
    visibility: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update message channels matching a filter.

    Args:
        filter_id_in: List of channel IDs to update.
        visibility: New visibility value.
    """
    items = await get_client().update_many_messageChannels(
        get_user_token(), filter_id_in, visibility,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_messageChannel_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a message channel by ID.

    Args:
        id: The unique ID of the message channel to delete (required).
    """
    return await get_client().delete_messageChannel_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_messageChannels(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete message channels matching a filter.

    Args:
        filter_id_in: List of channel IDs to delete.
    """
    items = await get_client().delete_many_messageChannels(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# MessageParticipant Tools
# =============================================================================

@mcp.tool()
async def get_all_messageParticipants(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all message participant records.

    Args:
        include_all_fields: When False (default), each participant contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messageParticipants(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_messageParticipant_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single message participant by ID.

    Args:
        id: The unique ID of the participant (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_messageParticipant_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_messageParticipant(
    messageId: str,
    role: Optional[str] = None,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    personId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new message participant.

    Args:
        messageId: ID of the associated message (required).
        role: Participant role.
        handle: Email handle.
        displayName: Display name.
        personId: ID of associated person.
    """
    return await get_client().create_messageParticipant(
        get_user_token(), messageId, role, handle, displayName, personId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_messageParticipant(
    id: str,
    role: Optional[str] = None,
    handle: Optional[str] = None,
    displayName: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing message participant.

    Args:
        id: The unique ID of the participant to update (required).
        role: New role.
        handle: New handle.
        displayName: New display name.
    """
    return await get_client().update_messageParticipant(
        id, get_user_token(), role, handle, displayName,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_messageParticipants(
    filter_id_in: Optional[list[str]] = None,
    role: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update message participants matching a filter.

    Args:
        filter_id_in: List of participant IDs to update.
        role: New role value.
    """
    items = await get_client().update_many_messageParticipants(
        get_user_token(), filter_id_in, role,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_messageParticipant_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a message participant by ID.

    Args:
        id: The unique ID of the participant to delete (required).
    """
    return await get_client().delete_messageParticipant_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_messageParticipants(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete message participants matching a filter.

    Args:
        filter_id_in: List of participant IDs to delete.
    """
    items = await get_client().delete_many_messageParticipants(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# MessageFolder Tools
# =============================================================================

@mcp.tool()
async def get_all_messageFolders(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all message folder records.

    Args:
        include_all_fields: When False (default), each folder contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messageFolders(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_messageFolder_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single message folder by ID.

    Args:
        id: The unique ID of the message folder (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_messageFolder_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_messageFolder(
    name: Optional[str] = None,
    messageChannelId: Optional[str] = None,
    isSentFolder: Optional[bool] = None,
    isSynced: Optional[bool] = None,
    pendingSyncAction: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new message folder.

    Args:
        name: Folder name.
        messageChannelId: ID of the associated message channel.
        isSentFolder: Whether this is a sent folder.
        isSynced: Whether the folder is synced.
        pendingSyncAction: Pending sync action.
    """
    return await get_client().create_messageFolder(
        get_user_token(), name, messageChannelId, isSentFolder, isSynced, pendingSyncAction,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_messageFolder(
    id: str,
    name: Optional[str] = None,
    isSynced: Optional[bool] = None,
    pendingSyncAction: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing message folder.

    Args:
        id: The unique ID of the message folder to update (required).
        name: New name.
        isSynced: New synced state.
        pendingSyncAction: New pending sync action.
    """
    return await get_client().update_messageFolder(
        id, get_user_token(), name, isSynced, pendingSyncAction,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_messageFolders(
    filter_id_in: Optional[list[str]] = None,
    isSynced: Optional[bool] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update message folders matching a filter.

    Args:
        filter_id_in: List of folder IDs to update.
        isSynced: New synced state.
    """
    items = await get_client().update_many_messageFolders(
        get_user_token(), filter_id_in, isSynced,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_messageFolder_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a message folder by ID.

    Args:
        id: The unique ID of the message folder to delete (required).
    """
    return await get_client().delete_messageFolder_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_messageFolders(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete message folders matching a filter.

    Args:
        filter_id_in: List of folder IDs to delete.
    """
    items = await get_client().delete_many_messageFolders(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# MessageChannelMessageAssociation Tools
# =============================================================================

@mcp.tool()
async def get_all_messageChannelMessageAssociations(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all message channel message association records.

    Args:
        include_all_fields: When False (default), each association contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_messageChannelMessageAssociations(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_messageChannelMessageAssociation_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single message channel message association by ID.

    Args:
        id: The unique ID of the association (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_messageChannelMessageAssociation_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_messageChannelMessageAssociation(
    messageChannelId: str,
    messageId: str,
    direction: Optional[str] = None,
    messageThreadId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new message channel message association.

    Args:
        messageChannelId: ID of the message channel (required).
        messageId: ID of the message (required).
        direction: Message direction (e.g. INCOMING, OUTGOING).
        messageThreadId: ID of the message thread.
    """
    return await get_client().create_messageChannelMessageAssociation(
        get_user_token(), messageChannelId, messageId, direction, messageThreadId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_messageChannelMessageAssociation(
    id: str,
    direction: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing message channel message association.

    Args:
        id: The unique ID of the association to update (required).
        direction: New direction value.
    """
    return await get_client().update_messageChannelMessageAssociation(
        id, get_user_token(), direction,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_messageChannelMessageAssociations(
    filter_id_in: Optional[list[str]] = None,
    direction: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update message channel message associations matching a filter.

    Args:
        filter_id_in: List of association IDs to update.
        direction: New direction value.
    """
    items = await get_client().update_many_messageChannelMessageAssociations(
        get_user_token(), filter_id_in, direction,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_messageChannelMessageAssociation_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a message channel message association by ID.

    Args:
        id: The unique ID of the association to delete (required).
    """
    return await get_client().delete_messageChannelMessageAssociation_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_messageChannelMessageAssociations(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete message channel message associations matching a filter.

    Args:
        filter_id_in: List of association IDs to delete.
    """
    items = await get_client().delete_many_messageChannelMessageAssociations(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# NoteTarget Tools
# =============================================================================

@mcp.tool()
async def get_all_noteTargets(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all note target records.

    Args:
        include_all_fields: When False (default), each target contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_noteTargets(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_noteTarget_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single note target by ID.

    Args:
        id: The unique ID of the note target (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_noteTarget_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_noteTarget(
    noteId: str,
    personId: Optional[str] = None,
    companyId: Optional[str] = None,
    opportunityId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new note target.

    Args:
        noteId: ID of the associated note (required).
        personId: ID of associated person.
        companyId: ID of associated company.
        opportunityId: ID of associated opportunity.
    """
    return await get_client().create_noteTarget(
        get_user_token(), noteId, personId, companyId, opportunityId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_noteTarget(
    id: str,
    personId: Optional[str] = None,
    companyId: Optional[str] = None,
    opportunityId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing note target.

    Args:
        id: The unique ID of the note target to update (required).
        personId: New person ID.
        companyId: New company ID.
        opportunityId: New opportunity ID.
    """
    return await get_client().update_noteTarget(
        id, get_user_token(), personId, companyId, opportunityId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_noteTargets(
    filter_id_in: Optional[list[str]] = None,
    personId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update note targets matching a filter.

    Args:
        filter_id_in: List of note target IDs to update.
        personId: New person ID.
    """
    items = await get_client().update_many_noteTargets(
        get_user_token(), filter_id_in, personId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_noteTarget_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a note target by ID.

    Args:
        id: The unique ID of the note target to delete (required).
    """
    return await get_client().delete_noteTarget_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_noteTargets(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete note targets matching a filter.

    Args:
        filter_id_in: List of note target IDs to delete.
    """
    items = await get_client().delete_many_noteTargets(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# TaskTarget Tools
# =============================================================================

@mcp.tool()
async def get_all_taskTargets(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all task target records.

    Args:
        include_all_fields: When False (default), each target contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_taskTargets(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_taskTarget_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single task target by ID.

    Args:
        id: The unique ID of the task target (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_taskTarget_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_taskTarget(
    taskId: str,
    personId: Optional[str] = None,
    companyId: Optional[str] = None,
    opportunityId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new task target.

    Args:
        taskId: ID of the associated task (required).
        personId: ID of associated person.
        companyId: ID of associated company.
        opportunityId: ID of associated opportunity.
    """
    return await get_client().create_taskTarget(
        get_user_token(), taskId, personId, companyId, opportunityId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_taskTarget(
    id: str,
    personId: Optional[str] = None,
    companyId: Optional[str] = None,
    opportunityId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing task target.

    Args:
        id: The unique ID of the task target to update (required).
        personId: New person ID.
        companyId: New company ID.
        opportunityId: New opportunity ID.
    """
    return await get_client().update_taskTarget(
        id, get_user_token(), personId, companyId, opportunityId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_taskTargets(
    filter_id_in: Optional[list[str]] = None,
    personId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update task targets matching a filter.

    Args:
        filter_id_in: List of task target IDs to update.
        personId: New person ID.
    """
    items = await get_client().update_many_taskTargets(
        get_user_token(), filter_id_in, personId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_taskTarget_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a task target by ID.

    Args:
        id: The unique ID of the task target to delete (required).
    """
    return await get_client().delete_taskTarget_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_taskTargets(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete task targets matching a filter.

    Args:
        filter_id_in: List of task target IDs to delete.
    """
    items = await get_client().delete_many_taskTargets(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# TimelineActivity Tools
# =============================================================================

@mcp.tool()
async def get_all_timelineActivities(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all timeline activity records.

    Args:
        include_all_fields: When False (default), each activity contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_timelineActivities(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_timelineActivity_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single timeline activity by ID.

    Args:
        id: The unique ID of the timeline activity (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_timelineActivity_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_timelineActivity(
    name: str,
    happensAt: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    workspaceMemberId: Optional[str] = None,
    personId: Optional[str] = None,
    companyId: Optional[str] = None,
    opportunityId: Optional[str] = None,
    noteId: Optional[str] = None,
    taskId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new timeline activity.

    Args:
        name: Name of the activity (required).
        happensAt: Timestamp in ISO 8601 format with explicit UTC offset.
        properties: Nested properties object.
        workspaceMemberId: ID of the workspace member.
        personId: ID of associated person.
        companyId: ID of associated company.
        opportunityId: ID of associated opportunity.
        noteId: ID of associated note.
        taskId: ID of associated task.
    """
    return await get_client().create_timelineActivity(
        get_user_token(), name, happensAt, properties, workspaceMemberId,
        personId, companyId, opportunityId, noteId, taskId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_timelineActivity(
    id: str,
    name: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing timeline activity.

    Args:
        id: The unique ID of the timeline activity to update (required).
        name: New name.
        properties: New properties object.
    """
    return await get_client().update_timelineActivity(
        id, get_user_token(), name, properties,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_timelineActivities(
    filter_id_in: Optional[list[str]] = None,
    properties: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update timeline activities matching a filter.

    Args:
        filter_id_in: List of timeline activity IDs to update.
        properties: New properties object.
    """
    items = await get_client().update_many_timelineActivities(
        get_user_token(), filter_id_in, properties,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_timelineActivity_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a timeline activity by ID.

    Args:
        id: The unique ID of the timeline activity to delete (required).
    """
    return await get_client().delete_timelineActivity_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_timelineActivities(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete timeline activities matching a filter.

    Args:
        filter_id_in: List of timeline activity IDs to delete.
    """
    items = await get_client().delete_many_timelineActivities(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# WorkspaceMember Tools (read-only)
# =============================================================================

@mcp.tool()
async def get_all_workspaceMembers(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all workspace member records.

    Args:
        include_all_fields: When False (default), each member contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_workspaceMembers(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_workspaceMember_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single workspace member by ID.

    Args:
        id: The unique ID of the workspace member (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_workspaceMember_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def delete_workspaceMember_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a workspace member by ID.

    Args:
        id: The unique ID of the workspace member to delete (required).
    """
    return await get_client().delete_workspaceMember_by_id(id, get_user_token())

# =============================================================================
# ConnectedAccount Tools
# =============================================================================

@mcp.tool()
async def get_all_connectedAccounts(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all connected account records.

    Args:
        include_all_fields: When False (default), each account contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_connectedAccounts(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_connectedAccount_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single connected account by ID.

    Args:
        id: The unique ID of the connected account (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_connectedAccount_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_connectedAccount(
    handle: str,
    provider: str,
    accessToken: Optional[str] = None,
    refreshToken: Optional[str] = None,
    visibility: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new connected account.

    Args:
        handle: Email handle/address (required).
        provider: Provider name e.g. google (required).
        accessToken: Access token.
        refreshToken: Refresh token.
        visibility: Visibility setting (default: user).
    """
    return await get_client().create_connectedAccount(
        get_user_token(), handle, provider, accessToken, refreshToken, visibility,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_connectedAccount(
    id: str,
    handle: Optional[str] = None,
    visibility: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing connected account.

    Args:
        id: The unique ID of the connected account to update (required).
        handle: New handle.
        visibility: New visibility.
    """
    return await get_client().update_connectedAccount(
        id, get_user_token(), handle, visibility,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_connectedAccounts(
    filter_id_in: Optional[list[str]] = None,
    visibility: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update connected accounts matching a filter.

    Args:
        filter_id_in: List of connected account IDs to update.
        visibility: New visibility value.
    """
    items = await get_client().update_many_connectedAccounts(
        get_user_token(), filter_id_in, visibility,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_connectedAccount_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a connected account by ID.

    Args:
        id: The unique ID of the connected account to delete (required).
    """
    return await get_client().delete_connectedAccount_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_connectedAccounts(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete connected accounts matching a filter.

    Args:
        filter_id_in: List of connected account IDs to delete.
    """
    items = await get_client().delete_many_connectedAccounts(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# FavoriteFolder Tools
# =============================================================================

@mcp.tool()
async def get_all_favoriteFolders(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all favorite folder records.

    Args:
        include_all_fields: When False (default), each folder contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_favoriteFolders(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_favoriteFolder_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single favorite folder by ID.

    Args:
        id: The unique ID of the favorite folder (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_favoriteFolder_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_favoriteFolder(
    name: Optional[str] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new favorite folder.

    Args:
        name: Folder name.
    """
    return await get_client().create_favoriteFolder(
        get_user_token(), name,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_favoriteFolder(
    id: str,
    name: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing favorite folder.

    Args:
        id: The unique ID of the favorite folder to update (required).
        name: New name.
    """
    return await get_client().update_favoriteFolder(
        id, get_user_token(), name,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_favoriteFolders(
    filter_id_in: Optional[list[str]] = None,
    name: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update favorite folders matching a filter.

    Args:
        filter_id_in: List of folder IDs to update.
        name: New name value.
    """
    items = await get_client().update_many_favoriteFolders(
        get_user_token(), filter_id_in, name,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_favoriteFolder_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a favorite folder by ID.

    Args:
        id: The unique ID of the favorite folder to delete (required).
    """
    return await get_client().delete_favoriteFolder_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_favoriteFolders(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete favorite folders matching a filter.

    Args:
        filter_id_in: List of folder IDs to delete.
    """
    items = await get_client().delete_many_favoriteFolders(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Dashboard Tools
# =============================================================================

@mcp.tool()
async def get_all_dashboards(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all dashboard records.

    Args:
        include_all_fields: When False (default), each dashboard contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_dashboards(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_dashboard_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single dashboard by ID.

    Args:
        id: The unique ID of the dashboard (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_dashboard_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_dashboard(
    title: Optional[str] = None,
    pageLayoutId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new dashboard.

    Args:
        title: Dashboard title.
        pageLayoutId: ID of the page layout.
        position: Display position.
    """
    return await get_client().create_dashboard(
        get_user_token(), title, pageLayoutId, position,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_dashboard(
    id: str,
    title: Optional[str] = None,
    pageLayoutId: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing dashboard.

    Args:
        id: The unique ID of the dashboard to update (required).
        title: New title.
        pageLayoutId: New page layout ID.
        position: New position.
    """
    return await get_client().update_dashboard(
        id, get_user_token(), title, pageLayoutId, position,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_dashboards(
    filter_id_in: Optional[list[str]] = None,
    title: Optional[str] = None,
    position: Optional[int] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update dashboards matching a filter.

    Args:
        filter_id_in: List of dashboard IDs to update.
        title: New title value.
        position: New position value.
    """
    items = await get_client().update_many_dashboards(
        get_user_token(), filter_id_in, title, position,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_dashboard_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a dashboard by ID.

    Args:
        id: The unique ID of the dashboard to delete (required).
    """
    return await get_client().delete_dashboard_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_dashboards(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete dashboards matching a filter.

    Args:
        filter_id_in: List of dashboard IDs to delete.
    """
    items = await get_client().delete_many_dashboards(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Blocklist Tools
# =============================================================================

@mcp.tool()
async def get_all_blocklists(
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all blocklist records.

    Args:
        include_all_fields: When False (default), each blocklist entry contains only
            commonly used fields. Set to True to include all fields.
    """
    data = await get_client().get_all_blocklists(
        get_user_token(),
        include_all_fields=include_all_fields if ALLOW_ALL_AGGREGATE else False
    )
    return {"items": json_to_toon(data)}

@mcp.tool()
async def get_blocklist_by_id(
    id: str,
    include_all_fields: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a single blocklist entry by ID.

    Args:
        id: The unique ID of the blocklist entry (required).
        include_all_fields: When False (default), returns only commonly used
            fields. Set to True to retrieve all available fields.
    """
    return await get_client().get_blocklist_by_id(
        id, get_user_token(), include_all_fields=include_all_fields
    )

@mcp.tool()
async def create_blocklist(
    handle: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a new blocklist entry.

    Args:
        handle: Email handle to block.
        workspaceMemberId: ID of the workspace member.
    """
    return await get_client().create_blocklist(
        get_user_token(), handle, workspaceMemberId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_blocklist(
    id: str,
    handle: Optional[str] = None,
    workspaceMemberId: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an existing blocklist entry.

    Args:
        id: The unique ID of the blocklist entry to update (required).
        handle: New email handle.
        workspaceMemberId: ID of the workspace member.
    """
    return await get_client().update_blocklist(
        id, get_user_token(), handle, workspaceMemberId,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )

@mcp.tool()
async def update_many_blocklists(
    filter_id_in: Optional[list[str]] = None,
    handle: Optional[str] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk update blocklist entries matching a filter.

    Args:
        filter_id_in: List of blocklist entry IDs to update.
        handle: New handle value.
    """
    items = await get_client().update_many_blocklists(
        get_user_token(), filter_id_in, handle,
        include_all_fields=ALLOW_ALL_AGGREGATE
    )
    return {"items": items}

@mcp.tool()
async def delete_blocklist_by_id(
    id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a blocklist entry by ID.

    Args:
        id: The unique ID of the blocklist entry to delete (required).
    """
    return await get_client().delete_blocklist_by_id(id, get_user_token())

@mcp.tool()
async def delete_many_blocklists(
    filter_id_in: Optional[list[str]] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk delete blocklist entries matching a filter.

    Args:
        filter_id_in: List of blocklist entry IDs to delete.
    """
    items = await get_client().delete_many_blocklists(get_user_token(), filter_id_in)
    return {"items": items}

# =============================================================================
# Server Health Check
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
                headers={"Authorization": f"Bearer {get_user_token() or ''}"},
            )
            return {"status": "connected", "backend_response": response.status_code}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}

# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the MCP server."""
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