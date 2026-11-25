from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

from app.core.pagination import Page
from app.core.query import contains_pattern
from app.core.repository import BaseRepository
from app.modules.buildings.models import Building
from app.modules.flats.models import Flat
from app.modules.leases.models import Lease
from app.modules.users.models import User


@dataclass(frozen=True)
class LeaseFilters:
    q: str | None = None
    is_active: bool | None = None
    tenant_id: int | None = None  # set by the service for tenants ("own" data only)


class LeaseRepository(BaseRepository[Lease]):
    model = Lease

    async def search(self, filters: LeaseFilters, page: Page) -> list[Lease]:
        tenant = aliased(User)
        flat = aliased(Flat)
        building = aliased(Building)
        stmt = (
            select(Lease)
            .join(tenant, Lease.tenant_id == tenant.id)
            .join(flat, Lease.flat_id == flat.id)
            .join(building, flat.building_id == building.id)
        )
        if filters.tenant_id is not None:
            stmt = stmt.where(Lease.tenant_id == filters.tenant_id)
        if filters.is_active is not None:
            stmt = stmt.where(Lease.is_active.is_(filters.is_active))
        if filters.q:
            pattern = contains_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    tenant.full_name.ilike(pattern),
                    tenant.phone.ilike(pattern),
                    flat.flat_no.ilike(pattern),
                    building.name.ilike(pattern),
                )
            )
        stmt = (
            stmt.order_by(Lease.is_active.desc(), building.name, flat.flat_no, Lease.start_date)
            .limit(page.limit)
            .offset(page.offset)
        )
        return list(await self.session.scalars(stmt))

    async def active_for_flat(self, flat_id: int, exclude_id: int | None = None) -> Lease | None:
        stmt = select(Lease).where(Lease.flat_id == flat_id, Lease.is_active.is_(True))
        if exclude_id is not None:
            stmt = stmt.where(Lease.id != exclude_id)
        return await self.session.scalar(stmt.limit(1))

    async def active_for_tenant(self, tenant_id: int) -> Lease | None:
        """The tenant's current lease (the newest, if they somehow have several)."""
        stmt = (
            select(Lease)
            .where(Lease.tenant_id == tenant_id, Lease.is_active.is_(True))
            .order_by(Lease.start_date.desc(), Lease.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def flat_has_any(self, flat_id: int) -> bool:
        stmt = select(Lease.id).where(Lease.flat_id == flat_id).limit(1)
        return await self.session.scalar(stmt) is not None

    async def list_active(self) -> list[Lease]:
        stmt = select(Lease).where(Lease.is_active.is_(True)).order_by(Lease.id)
        return list(await self.session.scalars(stmt))
