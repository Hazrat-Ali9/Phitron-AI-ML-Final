"""Tools the chat model may call. Each tool calls the same services as the HTTP API.

A tool = name + description (the model reads it) + argument model (its JSON schema is
sent to the model and used to validate what comes back) + allowed roles + handler.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.pagination import Page
from app.core.validators import Month
from app.integrations.llm.types import ToolDefinition
from app.modules.flats.models import FlatStatus
from app.modules.flats.repositories import FlatFilters
from app.modules.flats.schemas import FlatOut
from app.modules.maintenance.schemas import MaintenanceCreate
from app.modules.users.models import RoleName, User
from app.services import Services

ALL_ROLES = frozenset(RoleName)


@dataclass(frozen=True)
class ToolContext:
    user: User
    services: Services


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")


Handler = Callable[[ToolContext, Any], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[ToolArgs]
    roles: frozenset[RoleName]
    handler: Handler

    def definition(self) -> ToolDefinition:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": _clean_schema(self.args_model.model_json_schema()),
            },
        }


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Drop pydantic's `title` keys; some providers reject unknown/unneeded keywords."""
    if isinstance(schema, dict):
        return {k: _clean_schema(v) for k, v in schema.items() if k != "title"}
    if isinstance(schema, list):
        return [_clean_schema(v) for v in schema]
    return schema


# ---- get_my_rent_status ---------------------------------------------------------------


class NoArgs(ToolArgs):
    pass


async def get_my_rent_status(ctx: ToolContext, _: NoArgs) -> dict[str, Any]:
    status = await ctx.services.payments.rent_status_for_tenant(ctx.user)
    return status.model_dump(mode="json")


# ---- list_vacant_flats ----------------------------------------------------------------


class VacantFlatsArgs(ToolArgs):
    area: str | None = Field(
        default=None, description="Neighbourhood, e.g. Mirpur, Dhanmondi, Uttara"
    )
    max_rent: int | None = Field(default=None, ge=0, description="Maximum monthly rent in taka")
    bedrooms: int | None = Field(default=None, ge=1, le=10, description="Exact bedroom count")


async def list_vacant_flats(ctx: ToolContext, args: VacantFlatsArgs) -> dict[str, Any]:
    filters = FlatFilters(
        status=FlatStatus.VACANT, area=args.area, max_rent=args.max_rent, bedrooms=args.bedrooms
    )
    flats = await ctx.services.flats.search(filters, Page(limit=10))
    return {
        "count": len(flats),
        "flats": [
            FlatOut.model_validate(flat).model_dump(
                include={
                    "flat_no",
                    "building_name",
                    "area",
                    "floor",
                    "bedrooms",
                    "bathrooms",
                    "size_sqft",
                    "monthly_rent",
                    "service_charge",
                    "description",
                }
            )
            for flat in flats
        ],
    }


# ---- create_maintenance_request ------------------------------------------------------


class MaintenanceArgs(ToolArgs):
    title: Annotated[str, StringConstraints(min_length=3, max_length=120)] = Field(
        description="Short summary, e.g. 'Kitchen sink leaking'"
    )
    description: Annotated[str, StringConstraints(min_length=5, max_length=2000)] = Field(
        description="The problem in the tenant's words"
    )
    category: Literal["plumbing", "electrical", "gas", "lift", "painting", "other"]
    priority: Literal["low", "medium", "high", "urgent"] = Field(
        default="medium",
        description="urgent = danger or no water/power/gas/lift; high = breaks daily life",
    )


async def create_maintenance_request(ctx: ToolContext, args: MaintenanceArgs) -> dict[str, Any]:
    request = await ctx.services.maintenance.create(
        ctx.user, MaintenanceCreate.model_validate(args.model_dump())
    )
    return {
        "request_id": request.id,
        "flat": f"{request.flat.flat_no}, {request.flat.building.name}",
        "title": request.title,
        "category": request.category.value,
        "priority": request.priority.value,
        "status": request.status.value,
    }


# ---- get_collection_summary ---------------------------------------------------------


class CollectionArgs(ToolArgs):
    month: Month | None = Field(
        default=None, description="Month as YYYY-MM. Leave empty for the current month."
    )


async def get_collection_summary(ctx: ToolContext, args: CollectionArgs) -> dict[str, Any]:
    summary = await ctx.services.payments.collection_summary(args.month)
    return summary.model_dump(mode="json")


# ---- search_knowledge ------------------------------------------------------------------


class KnowledgeArgs(ToolArgs):
    query: Annotated[str, StringConstraints(min_length=2, max_length=500)] = Field(
        description="The question, rephrased as a short search query (any language)"
    )


async def search_knowledge(ctx: ToolContext, args: KnowledgeArgs) -> dict[str, Any]:
    hits = await ctx.services.knowledge.search(args.query)
    if not hits:
        return {"results": [], "note": "nothing relevant found"}
    return {
        "results": [
            {"title": hit.title, "content": hit.content, "score": round(hit.score, 3)}
            for hit in hits
        ]
    }


# ---- registry -------------------------------------------------------------------------

TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in [
        Tool(
            name="get_my_rent_status",
            description=(
                "Get the logged-in tenant's own lease and rent records: each month's amount "
                "due, amount paid and status, plus the total outstanding. Use for questions "
                "like 'how much rent do I owe?' or 'did my October payment go through?'."
            ),
            args_model=NoArgs,
            roles=frozenset({RoleName.TENANT}),
            handler=get_my_rent_status,
        ),
        Tool(
            name="list_vacant_flats",
            description=(
                "List vacant flats available to rent (max 10), optionally filtered by area, "
                "maximum monthly rent and number of bedrooms."
            ),
            args_model=VacantFlatsArgs,
            roles=ALL_ROLES,
            handler=list_vacant_flats,
        ),
        Tool(
            name="create_maintenance_request",
            description=(
                "Create a repair request for the tenant's own flat (the flat is found "
                "automatically from their lease). Use when the tenant reports something "
                "broken, leaking or not working."
            ),
            args_model=MaintenanceArgs,
            roles=frozenset({RoleName.TENANT}),
            handler=create_maintenance_request,
        ),
        Tool(
            name="get_collection_summary",
            description=(
                "Rent collection report for one month across all buildings: expected, "
                "collected and outstanding totals, per-building totals and the tenants who "
                "have not paid in full."
            ),
            args_model=CollectionArgs,
            roles=frozenset({RoleName.ADMIN}),
            handler=get_collection_summary,
        ),
        Tool(
            name="search_knowledge",
            description=(
                "Search the building's documents: house rules, tenancy agreement terms "
                "(rent due date, late fee, advance, notice), utilities (DESCO/DPDC prepaid "
                "meter, Titas gas, WASA water, generator, internet), the Premises Rent Control "
                "Act 1991, move-in/move-out checklists and emergency contacts. Returns the "
                "most relevant passages, or no results if the documents do not cover it."
            ),
            args_model=KnowledgeArgs,
            roles=ALL_ROLES,
            handler=search_knowledge,
        ),
    ]
}


def tools_for_role(role: str) -> list[Tool]:
    """Only these definitions are sent to the model, so a tenant never sees admin tools."""
    return [tool for tool in TOOLS.values() if role in tool.roles]
