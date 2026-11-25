from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page
from app.modules.buildings.models import Building
from app.modules.buildings.repositories import BuildingRepository
from app.modules.buildings.schemas import BuildingCreate, BuildingUpdate
from app.modules.users.models import User


class BuildingService:
    def __init__(self, buildings: BuildingRepository) -> None:
        self.buildings = buildings

    async def search(
        self, page: Page, q: str | None = None, area: str | None = None
    ) -> list[Building]:
        return await self.buildings.search(page, q=q, area=area)

    async def get(self, building_id: int) -> Building:
        building = await self.buildings.get(building_id)
        if building is None:
            raise NotFoundError("Building not found")
        return building

    async def create(self, data: BuildingCreate, owner: User) -> Building:
        if await self.buildings.name_taken(data.name):
            raise ConflictError(f"A building named '{data.name}' already exists")
        building = Building(**data.model_dump(), owner_id=owner.id)
        await self.buildings.add(building)
        await self.buildings.commit()
        return building

    async def update(self, building_id: int, data: BuildingUpdate) -> Building:
        building = await self.get(building_id)
        changes = data.changes()
        if "name" in changes and await self.buildings.name_taken(
            changes["name"], exclude_id=building_id
        ):
            raise ConflictError(f"A building named '{changes['name']}' already exists")
        await self.buildings.update(building, changes)
        await self.buildings.commit()
        return building

    async def delete(self, building_id: int) -> None:
        building = await self.get(building_id)
        if await self.buildings.has_flats(building_id):
            raise ConflictError("This building still has flats. Delete or move them first.")
        await self.buildings.delete(building)
        await self.buildings.commit()
