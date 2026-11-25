from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import PageDep
from app.modules.auth.dependencies import AdminUser, CurrentUser
from app.modules.flats.dependencies import get_flat_service
from app.modules.flats.models import Flat, FlatStatus
from app.modules.flats.repositories import FlatFilters
from app.modules.flats.schemas import FlatCreate, FlatOut, FlatUpdate
from app.modules.flats.services import FlatService

router = APIRouter(prefix="/flats", tags=["flats"])

Service = Annotated[FlatService, Depends(get_flat_service)]


def get_flat_filters(
    q: Annotated[
        str | None, Query(max_length=100, description="Flat no, building name or description")
    ] = None,
    building_id: Annotated[int | None, Query(ge=1)] = None,
    area: Annotated[str | None, Query(max_length=60)] = None,
    status: Annotated[FlatStatus | None, Query()] = None,
    bedrooms: Annotated[int | None, Query(ge=1, le=10)] = None,
    min_rent: Annotated[int | None, Query(ge=0)] = None,
    max_rent: Annotated[int | None, Query(ge=0)] = None,
) -> FlatFilters:
    return FlatFilters(
        q=q,
        building_id=building_id,
        area=area,
        status=status,
        bedrooms=bedrooms,
        min_rent=min_rent,
        max_rent=max_rent,
    )


@router.get("", response_model=list[FlatOut], summary="List flats with filters")
async def list_flats(
    _: CurrentUser,
    service: Service,
    page: PageDep,
    filters: Annotated[FlatFilters, Depends(get_flat_filters)],
) -> list[Flat]:
    return await service.search(filters, page)


@router.get("/{flat_id}", response_model=FlatOut, summary="Get one flat")
async def get_flat(flat_id: int, _: CurrentUser, service: Service) -> Flat:
    return await service.get(flat_id)


@router.post(
    "",
    response_model=FlatOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a flat (admin)",
    responses={404: {"description": "Building not found"}, 409: {"description": "Duplicate"}},
)
async def create_flat(data: FlatCreate, _: AdminUser, service: Service) -> Flat:
    return await service.create(data)


@router.patch("/{flat_id}", response_model=FlatOut, summary="Update a flat (admin)")
async def update_flat(flat_id: int, data: FlatUpdate, _: AdminUser, service: Service) -> Flat:
    return await service.update(flat_id, data)


@router.delete(
    "/{flat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flat (admin)",
    responses={409: {"description": "Flat has an active lease"}},
)
async def delete_flat(flat_id: int, _: AdminUser, service: Service) -> None:
    await service.delete(flat_id)
