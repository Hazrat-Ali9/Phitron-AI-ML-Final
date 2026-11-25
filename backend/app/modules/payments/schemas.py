from datetime import datetime
from typing import Annotated

from pydantic import AliasPath, BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import PatchModel
from app.core.validators import Month
from app.modules.payments.models import PaymentMethod, PaymentStatus

Taka = Annotated[int, Field(ge=0, le=10_000_000)]
TrxId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class PaymentCreate(BaseModel):
    lease_id: int
    month: Month = Field(examples=["2026-11"])
    amount_due: Annotated[int, Field(gt=0, le=10_000_000)] | None = Field(
        default=None, description="Defaults to the lease's monthly rent"
    )
    amount_paid: Taka = 0
    method: PaymentMethod | None = None
    trx_id: TrxId | None = None
    paid_at: datetime | None = None


class PaymentUpdate(PatchModel):
    nullable_fields = frozenset({"method", "trx_id", "paid_at"})

    month: Month | None = None
    amount_due: Annotated[int, Field(gt=0, le=10_000_000)] | None = None
    amount_paid: Taka | None = None
    method: PaymentMethod | None = None
    trx_id: TrxId | None = None
    paid_at: datetime | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lease_id: int
    tenant_name: str = Field(validation_alias=AliasPath("lease", "tenant", "full_name"))
    flat_no: str = Field(validation_alias=AliasPath("lease", "flat", "flat_no"))
    building_name: str = Field(validation_alias=AliasPath("lease", "flat", "building", "name"))
    month: str
    amount_due: int
    amount_paid: int
    method: PaymentMethod | None
    trx_id: str | None
    paid_at: datetime | None
    status: PaymentStatus


# ---- reports (used by the chat tools and the MCP server) ---------------------------------


class RentMonthOut(BaseModel):
    month: str
    amount_due: int
    amount_paid: int
    outstanding: int
    status: PaymentStatus
    method: PaymentMethod | None
    paid_at: datetime | None


class RentStatusOut(BaseModel):
    has_active_lease: bool
    building: str | None = None
    flat_no: str | None = None
    monthly_rent: int | None = None
    lease_start: str | None = None
    months: list[RentMonthOut] = []
    total_outstanding: int = 0


class PendingTenantOut(BaseModel):
    tenant_name: str
    tenant_phone: str | None
    building: str
    flat_no: str
    amount_due: int
    amount_paid: int
    outstanding: int
    status: str  # paid | partial | due | no_record


class BuildingCollectionOut(BaseModel):
    building: str
    expected: int
    collected: int
    outstanding: int


class CollectionSummaryOut(BaseModel):
    month: str
    expected: int
    collected: int
    outstanding: int
    collection_rate_percent: float
    by_building: list[BuildingCollectionOut]
    pending_tenants: list[PendingTenantOut]
