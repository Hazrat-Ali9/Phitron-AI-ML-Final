from dataclasses import dataclass

from sqlalchemy import func, select

from app.core.pagination import Page
from app.core.repository import BaseRepository
from app.modules.flats.models import Flat
from app.modules.maintenance.models import (
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
)


@dataclass(frozen=True)
class MaintenanceFilters:
    status: MaintenanceStatus | None = None
    category: MaintenanceCategory | None = None
    priority: MaintenancePriority | None = None
    flat_id: int | None = None
    building_id: int | None = None
    reported_by_id: int | None = None  # set by the service for tenants ("own" data only)


class MaintenanceRepository(BaseRepository[MaintenanceRequest]):
    model = MaintenanceRequest

    async def search(self, filters: MaintenanceFilters, page: Page) -> list[MaintenanceRequest]:
        stmt = select(MaintenanceRequest)
        if filters.reported_by_id is not None:
            stmt = stmt.where(MaintenanceRequest.reported_by_id == filters.reported_by_id)
        if filters.status is not None:
            stmt = stmt.where(MaintenanceRequest.status == filters.status)
        if filters.category is not None:
            stmt = stmt.where(MaintenanceRequest.category == filters.category)
        if filters.priority is not None:
            stmt = stmt.where(MaintenanceRequest.priority == filters.priority)
        if filters.flat_id is not None:
            stmt = stmt.where(MaintenanceRequest.flat_id == filters.flat_id)
        if filters.building_id is not None:
            stmt = stmt.where(
                MaintenanceRequest.flat_id.in_(
                    select(Flat.id).where(Flat.building_id == filters.building_id)
                )
            )
        stmt = (
            stmt.order_by(MaintenanceRequest.created_at.desc(), MaintenanceRequest.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        return list(await self.session.scalars(stmt))

    async def count_open_by_building(self, building_id: int) -> int:
        stmt = (
            select(func.count(MaintenanceRequest.id))
            .join(Flat, MaintenanceRequest.flat_id == Flat.id)
            .where(
                Flat.building_id == building_id,
                MaintenanceRequest.status != MaintenanceStatus.RESOLVED,
            )
        )
        return await self.session.scalar(stmt) or 0

    async def flat_has_any(self, flat_id: int) -> bool:
        stmt = select(MaintenanceRequest.id).where(MaintenanceRequest.flat_id == flat_id).limit(1)
        return await self.session.scalar(stmt) is not None
