from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import PageDep
from app.modules.auth.dependencies import AdminUser, CurrentUser
from app.modules.buildings.dependencies import get_building_service
from app.modules.buildings.models import Building
from app.modules.buildings.schemas import BuildingCreate, BuildingOut, BuildingUpdate
from app.modules.buildings.services import BuildingService

router = APIRouter(prefix="/buildings", tags=["buildings"])

Service = Annotated[BuildingService, Depends(get_building_service)]


@router.get("", response_model=list[BuildingOut], summary="List buildings")
async def list_buildings(
    _: CurrentUser,
    service: Service,
    page: PageDep,
    q: Annotated[str | None, Query(max_length=100, description="Name or address")] = None,
    area: Annotated[str | None, Query(max_length=60)] = None,
) -> list[Building]:
    return await service.search(page, q=q, area=area)


@router.get("/{building_id}", response_model=BuildingOut, summary="Get one building")
async def get_building(building_id: int, _: CurrentUser, service: Service) -> Building:
    return await service.get(building_id)


@router.post(
    "",
    response_model=BuildingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a building (admin)",
    responses={409: {"description": "Name already used"}},
)
async def create_building(data: BuildingCreate, admin: AdminUser, service: Service) -> Building:
    return await service.create(data, owner=admin)


@router.patch("/{building_id}", response_model=BuildingOut, summary="Update a building (admin)")
async def update_building(
    building_id: int, data: BuildingUpdate, _: AdminUser, service: Service
) -> Building:
    return await service.update(building_id, data)


@router.delete(
    "/{building_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a building (admin)",
    responses={409: {"description": "Building still has flats"}},
)
async def delete_building(building_id: int, _: AdminUser, service: Service) -> None:
    await service.delete(building_id)
