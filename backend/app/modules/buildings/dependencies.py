from typing import Annotated

from fastapi import Depends

from app.modules.buildings.repositories import BuildingRepository
from app.modules.buildings.services import BuildingService
from app.modules.users.dependencies import DbSession


def get_building_repository(db: DbSession) -> BuildingRepository:
    return BuildingRepository(db)


def get_building_service(
    buildings: Annotated[BuildingRepository, Depends(get_building_repository)],
) -> BuildingService:
    return BuildingService(buildings)
