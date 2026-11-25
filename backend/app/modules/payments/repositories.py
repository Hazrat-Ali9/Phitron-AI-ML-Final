from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.core.pagination import Page
from app.core.repository import BaseRepository
from app.modules.buildings.models import Building
from app.modules.flats.models import Flat
from app.modules.leases.models import Lease
from app.modules.payments.models import PaymentStatus, RentPayment


@dataclass(frozen=True)
class PaymentFilters:
    month: str | None = None
    status: PaymentStatus | None = None
    lease_id: int | None = None
    tenant_id: int | None = None  # set by the service for tenants ("own" data only)


class PaymentRepository(BaseRepository[RentPayment]):
    model = RentPayment

    async def search(self, filters: PaymentFilters, page: Page | None = None) -> list[RentPayment]:
        lease = aliased(Lease)
        flat = aliased(Flat)
        building = aliased(Building)
        stmt = (
            select(RentPayment)
            .join(lease, RentPayment.lease_id == lease.id)
            .join(flat, lease.flat_id == flat.id)
            .join(building, flat.building_id == building.id)
        )
        if filters.tenant_id is not None:
            stmt = stmt.where(lease.tenant_id == filters.tenant_id)
        if filters.lease_id is not None:
            stmt = stmt.where(RentPayment.lease_id == filters.lease_id)
        if filters.month:
            stmt = stmt.where(RentPayment.month == filters.month)
        if filters.status is not None:
            stmt = stmt.where(RentPayment.status == filters.status)
        stmt = stmt.order_by(RentPayment.month.desc(), building.name, flat.flat_no)
        if page is not None:
            stmt = stmt.limit(page.limit).offset(page.offset)
        return list(await self.session.scalars(stmt))

    async def exists_for_month(
        self, lease_id: int, month: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(RentPayment.id).where(
            RentPayment.lease_id == lease_id, RentPayment.month == month
        )
        if exclude_id is not None:
            stmt = stmt.where(RentPayment.id != exclude_id)
        return await self.session.scalar(stmt.limit(1)) is not None
