"""Generic repository with the CRUD plumbing every module shares."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: int, *, refresh: bool = False) -> ModelT | None:
        # refresh=True re-reads the row and its eager-loaded relationships
        # (needed after an update changed a foreign key, e.g. flat.building_id).
        return await self.session.get(self.model, obj_id, populate_existing=refresh)

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: ModelT, values: dict[str, Any]) -> ModelT:
        for field, value in values.items():
            setattr(obj, field, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
