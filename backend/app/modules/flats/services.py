from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.core.pagination import Page
from app.modules.buildings.models import Building
from app.modules.buildings.repositories import BuildingRepository
from app.modules.flats.models import Flat, FlatStatus
from app.modules.flats.repositories import FlatFilters, FlatRepository
from app.modules.flats.schemas import FlatCreate, FlatUpdate
from app.modules.leases.repositories import LeaseRepository
from app.modules.maintenance.repositories import MaintenanceRepository


class FlatService:
    def __init__(
        self,
        flats: FlatRepository,
        buildings: BuildingRepository,
        leases: LeaseRepository,
        maintenance: MaintenanceRepository,
    ) -> None:
        self.flats = flats
        self.buildings = buildings
        self.leases = leases
        self.maintenance = maintenance

    async def search(self, filters: FlatFilters, page: Page) -> list[Flat]:
        return await self.flats.search(filters, page)

    async def get(self, flat_id: int) -> Flat:
        flat = await self.flats.get(flat_id)
        if flat is None:
            raise NotFoundError("Flat not found")
        return flat

    async def _get_building(self, building_id: int) -> Building:
        building = await self.buildings.get(building_id)
        if building is None:
            raise NotFoundError("Building not found")
        return building

    @staticmethod
    def _check_floor(floor: int, building: Building) -> None:
        if floor > building.total_floors:
            raise UnprocessableError(
                "floor", f"{building.name} only has {building.total_floors} floors"
            )

    async def _check_unique(
        self, building: Building, flat_no: str, exclude_id: int | None = None
    ) -> None:
        if await self.flats.flat_no_taken(building.id, flat_no, exclude_id=exclude_id):
            raise ConflictError(f"Flat {flat_no} already exists in {building.name}")

    async def _check_status(self, flat_id: int | None, new_status: FlatStatus) -> None:
        """`occupied` follows the leases: it is set when a lease starts and cleared when it ends."""
        has_lease = flat_id is not None and await self.leases.active_for_flat(flat_id) is not None
        if new_status == FlatStatus.OCCUPIED and not has_lease:
            raise UnprocessableError(
                "status", "A flat becomes occupied when you add a lease for it"
            )
        if new_status == FlatStatus.VACANT and has_lease:
            raise ConflictError("This flat has an active lease. End the lease first.")

    async def create(self, data: FlatCreate) -> Flat:
        building = await self._get_building(data.building_id)
        self._check_floor(data.floor, building)
        await self._check_unique(building, data.flat_no)
        if data.status != FlatStatus.VACANT:
            await self._check_status(None, data.status)

        flat = Flat(**data.model_dump())
        await self.flats.add(flat)
        await self.flats.commit()
        return await self.get_fresh(flat.id)

    async def update(self, flat_id: int, data: FlatUpdate) -> Flat:
        flat = await self.get(flat_id)
        changes = data.changes()

        building = flat.building
        if "building_id" in changes and changes["building_id"] != flat.building_id:
            building = await self._get_building(changes["building_id"])
        self._check_floor(changes.get("floor", flat.floor), building)
        if "building_id" in changes or "flat_no" in changes:
            await self._check_unique(
                building, changes.get("flat_no", flat.flat_no), exclude_id=flat.id
            )
        if "status" in changes and changes["status"] != flat.status:
            await self._check_status(flat.id, changes["status"])

        await self.flats.update(flat, changes)
        await self.flats.commit()
        return await self.get_fresh(flat.id)

    async def delete(self, flat_id: int) -> None:
        flat = await self.get(flat_id)
        if await self.leases.active_for_flat(flat.id):
            raise ConflictError("This flat has an active lease. End the lease first.")
        if await self.leases.flat_has_any(flat.id) or await self.maintenance.flat_has_any(flat.id):
            # Keep the rent and repair history intact.
            raise ConflictError(
                "This flat has past leases or repair records, so it cannot be deleted"
            )
        await self.flats.delete(flat)
        await self.flats.commit()

    async def get_fresh(self, flat_id: int) -> Flat:
        """Re-read a flat together with its (possibly changed) building."""
        flat = await self.flats.get(flat_id, refresh=True)
        if flat is None:
            raise NotFoundError("Flat not found")
        return flat
