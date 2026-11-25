"""BariBhara MCP server: tools, a resource and a prompt over the same services as the API.

Served two ways from this one instance:
- streamable HTTP at /mcp, mounted inside the FastAPI app (see app/main.py)
- stdio, for desktop MCP clients: `uv run python -m scripts.mcp_stdio`

MCP calls have no logged-in user, so they act as the building owner (the first active
admin): e.g. a repair request created over MCP is "reported by" the owner.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from app import models  # noqa: F401  (register all models)
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.pagination import Page
from app.core.validators import validate_month
from app.integrations.embeddings.dependencies import get_embedding_client
from app.modules.flats.models import FlatStatus
from app.modules.flats.repositories import FlatFilters
from app.modules.flats.schemas import FlatOut
from app.modules.maintenance.models import MaintenanceCategory, MaintenancePriority
from app.modules.maintenance.schemas import MaintenanceCreate, MaintenanceOut
from app.modules.users.models import RoleName, User
from app.services import Services

mcp = MCPServer(
    name="BariBhara",
    title="BariBhara — rent & building management (Dhaka)",
    instructions=(
        "Tools for a small Dhaka landlord's buildings: find vacant flats, see who still owes "
        "rent this month, log repair requests and search the house rules / tenancy documents. "
        "Amounts are whole Bangladeshi taka (৳). Calls act as the building owner."
    ),
    version="0.1.0",
)


@asynccontextmanager
async def _services() -> AsyncIterator[Services]:
    """A fresh DB session per MCP call. Business errors become readable tool errors."""
    async with SessionLocal() as session:
        try:
            yield Services(session, get_embedding_client())
        except AppError as exc:
            raise ToolError(exc.message) from exc


async def _owner(services: Services) -> User:
    owner = await services.users_repo.first_with_role(RoleName.ADMIN)
    if owner is None:
        raise ToolError("No admin user exists yet. Run the seed script first.")
    return owner


def _month(month: str | None) -> str:
    month = month or date.today().strftime("%Y-%m")
    try:
        return validate_month(month)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


# ---- tools ----------------------------------------------------------------------------


@mcp.tool(title="List vacant flats")
async def list_vacant_flats(
    area: Annotated[str | None, Field(description="e.g. Mirpur, Dhanmondi, Uttara")] = None,
    max_rent: Annotated[int | None, Field(ge=0, description="Max monthly rent (৳)")] = None,
    bedrooms: Annotated[int | None, Field(ge=1, le=10)] = None,
) -> list[dict[str, Any]]:
    """Vacant flats available to rent (at most 20), ordered by building and flat number."""
    async with _services() as services:
        flats = await services.flats.search(
            FlatFilters(status=FlatStatus.VACANT, area=area, max_rent=max_rent, bedrooms=bedrooms),
            Page(limit=20),
        )
        return [FlatOut.model_validate(f).model_dump(mode="json") for f in flats]


@mcp.tool(title="Rent due summary")
async def get_rent_due_summary(
    month: Annotated[str | None, Field(description="YYYY-MM; empty = this month")] = None,
) -> dict[str, Any]:
    """Expected, collected and outstanding rent for a month, per building, plus the
    tenants who have not paid in full."""
    async with _services() as services:
        summary = await services.payments.collection_summary(_month(month))
        return summary.model_dump(mode="json")


@mcp.tool(title="Create a repair request")
async def create_maintenance_request(
    flat_id: Annotated[int, Field(ge=1, description="Flat id (see list_vacant_flats / API)")],
    title: Annotated[str, Field(min_length=3, max_length=120)],
    description: Annotated[str, Field(min_length=5, max_length=2000)],
    category: MaintenanceCategory,
    priority: MaintenancePriority = MaintenancePriority.MEDIUM,
) -> dict[str, Any]:
    """Log a maintenance/repair request for a flat (reported by the owner)."""
    async with _services() as services:
        request = await services.maintenance.create(
            await _owner(services),
            MaintenanceCreate(
                flat_id=flat_id,
                title=title,
                description=description,
                category=category,
                priority=priority,
            ),
        )
        return MaintenanceOut.model_validate(request).model_dump(mode="json")


@mcp.tool(title="Search building documents")
async def search_building_documents(
    query: Annotated[str, Field(min_length=2, max_length=500)],
) -> dict[str, Any]:
    """Search house rules, tenancy terms, utilities guide, Rent Control Act summary,
    move-in/out guide and emergency contacts. Empty results = not covered."""
    async with _services() as services:
        hits = await services.knowledge.search(query)
        return {
            "results": [
                {"title": h.title, "content": h.content, "score": round(h.score, 3)} for h in hits
            ]
        }


# ---- resource -------------------------------------------------------------------------


@mcp.resource(
    "baribhara://buildings/{building_id}/summary",
    name="building_summary",
    title="Building summary",
    description="Address, occupancy, vacant flats, this month's rent collection and open repairs",
    mime_type="application/json",
)
async def building_summary(building_id: int) -> dict[str, Any]:
    async with _services() as services:
        building = await services.buildings.get(int(building_id))
        flats = await services.flats.search(FlatFilters(building_id=building.id), Page(limit=200))
        month = date.today().strftime("%Y-%m")
        collection = await services.payments.collection_summary(month)
        totals = next((b for b in collection.by_building if b.building == building.name), None)
        occupied = sum(1 for f in flats if f.status == FlatStatus.OCCUPIED)
        return {
            "id": building.id,
            "name": building.name,
            "address": building.address,
            "area": building.area,
            "total_floors": building.total_floors,
            "flats": len(flats),
            "occupied": occupied,
            "occupancy_percent": round(100 * occupied / len(flats), 1) if flats else 0.0,
            "vacant_flats": [
                {"flat_no": f.flat_no, "bedrooms": f.bedrooms, "monthly_rent": f.monthly_rent}
                for f in flats
                if f.status == FlatStatus.VACANT
            ],
            "under_maintenance": [f.flat_no for f in flats if f.status == FlatStatus.MAINTENANCE],
            "collection_this_month": {
                "month": month,
                "expected": totals.expected if totals else 0,
                "collected": totals.collected if totals else 0,
                "outstanding": totals.outstanding if totals else 0,
            },
            "open_repairs": await services.maintenance.open_count_for_building(building.id),
        }


# ---- prompt ---------------------------------------------------------------------------


@mcp.prompt(title="Rent reminder SMS")
def rent_reminder(
    tenant_name: str,
    amount_due: str,
    month: str,
    language: Literal["bn", "en"] = "bn",
) -> str:
    """Draft a polite rent reminder SMS for a tenant."""
    lang = "Bangla (বাংলা script)" if language == "bn" else "simple English"
    return (
        f"Write a short, polite rent reminder SMS in {lang} from the building owner to the "
        f"tenant {tenant_name}.\n"
        f"- Rent due for {month}: ৳{amount_due}.\n"
        "- Rent is due by the 7th of the month; after the 10th a late fee of ৳500 is added.\n"
        "- They can pay by bKash, Nagad, bank transfer or cash to the caretaker, and should "
        "keep the transaction ID.\n"
        "- If they have already paid, ask them to ignore the message.\n"
        "Keep it under 300 characters, warm and respectful (use 'আপনি' in Bangla), no threats. "
        "Sign it as 'BariBhara building management'. Return only the SMS text."
    )
