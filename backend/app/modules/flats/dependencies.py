from typing import Annotated

from fastapi import Depends

from app.modules.buildings.dependencies import get_building_repository
from app.modules.buildings.repositories import BuildingRepository
from app.modules.flats.repositories import FlatRepository
from app.modules.flats.services import FlatService
from app.modules.leases.repositories import LeaseRepository
from app.modules.maintenance.repositories import MaintenanceRepository
from app.modules.users.dependencies import DbSession


def get_flat_repository(db: DbSession) -> FlatRepository:
    return FlatRepository(db)


def get_flat_service(
    db: DbSession,
    flats: Annotated[FlatRepository, Depends(get_flat_repository)],
    buildings: Annotated[BuildingRepository, Depends(get_building_repository)],
) -> FlatService:
    # Lease/maintenance repositories are built here directly (not via their modules'
    # dependency functions) to avoid a circular import between the flats and leases modules.
    return FlatService(flats, buildings, LeaseRepository(db), MaintenanceRepository(db))
