from sqlalchemy import func, or_, select

from app.core.pagination import Page
from app.core.query import contains_pattern
from app.core.repository import BaseRepository
from app.modules.buildings.models import Building
from app.modules.flats.models import Flat


class BuildingRepository(BaseRepository[Building]):
    model = Building

    async def search(
        self, page: Page, q: str | None = None, area: str | None = None
    ) -> list[Building]:
        stmt = select(Building)
        if q:
            pattern = contains_pattern(q)
            stmt = stmt.where(or_(Building.name.ilike(pattern), Building.address.ilike(pattern)))
        if area:
            stmt = stmt.where(func.lower(Building.area) == area.strip().lower())
        stmt = stmt.order_by(Building.name).limit(page.limit).offset(page.offset)
        return list(await self.session.scalars(stmt))

    async def name_taken(self, name: str, exclude_id: int | None = None) -> bool:
        stmt = select(Building.id).where(func.lower(Building.name) == name.lower())
        if exclude_id is not None:
            stmt = stmt.where(Building.id != exclude_id)
        return await self.session.scalar(stmt.limit(1)) is not None

    async def has_flats(self, building_id: int) -> bool:
        stmt = select(Flat.id).where(Flat.building_id == building_id).limit(1)
        return await self.session.scalar(stmt) is not None
