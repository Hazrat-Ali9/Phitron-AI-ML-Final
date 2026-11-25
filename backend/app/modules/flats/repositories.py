from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import contains_eager

from app.core.pagination import Page
from app.core.query import contains_pattern
from app.core.repository import BaseRepository
from app.modules.buildings.models import Building
from app.modules.flats.models import Flat, FlatStatus


@dataclass(frozen=True)
class FlatFilters:
    q: str | None = None
    building_id: int | None = None
    area: str | None = None
    status: FlatStatus | None = None
    bedrooms: int | None = None
    min_rent: int | None = None
    max_rent: int | None = None


class FlatRepository(BaseRepository[Flat]):
    model = Flat

    def _filtered(self, filters: FlatFilters) -> Select[tuple[Flat]]:
        # Join the building once and reuse it for filtering, ordering and FlatOut fields.
        stmt = select(Flat).join(Flat.building).options(contains_eager(Flat.building))
        if filters.q:
            pattern = contains_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    Flat.flat_no.ilike(pattern),
                    Building.name.ilike(pattern),
                    Flat.description.ilike(pattern),
                )
            )
        if filters.building_id is not None:
            stmt = stmt.where(Flat.building_id == filters.building_id)
        if filters.area:
            stmt = stmt.where(func.lower(Building.area) == filters.area.strip().lower())
        if filters.status is not None:
            stmt = stmt.where(Flat.status == filters.status)
        if filters.bedrooms is not None:
            stmt = stmt.where(Flat.bedrooms == filters.bedrooms)
        if filters.min_rent is not None:
            stmt = stmt.where(Flat.monthly_rent >= filters.min_rent)
        if filters.max_rent is not None:
            stmt = stmt.where(Flat.monthly_rent <= filters.max_rent)
        return stmt

    async def search(self, filters: FlatFilters, page: Page) -> list[Flat]:
        stmt = (
            self._filtered(filters)
            .order_by(Building.name, Flat.flat_no)
            .limit(page.limit)
            .offset(page.offset)
        )
        return list(await self.session.scalars(stmt))

    async def flat_no_taken(
        self, building_id: int, flat_no: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(Flat.id).where(Flat.building_id == building_id, Flat.flat_no == flat_no)
        if exclude_id is not None:
            stmt = stmt.where(Flat.id != exclude_id)
        return await self.session.scalar(stmt.limit(1)) is not None

    async def set_status(self, flat: Flat, status: FlatStatus) -> None:
        flat.status = status
        await self.session.flush()
