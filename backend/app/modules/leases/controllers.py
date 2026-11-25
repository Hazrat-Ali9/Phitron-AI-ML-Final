from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import PageDep
from app.modules.auth.dependencies import AdminUser, TenantOrAdminUser
from app.modules.leases.dependencies import get_lease_service
from app.modules.leases.models import Lease
from app.modules.leases.repositories import LeaseFilters
from app.modules.leases.schemas import LeaseCreate, LeaseOut, LeaseUpdate
from app.modules.leases.services import LeaseService

router = APIRouter(prefix="/leases", tags=["leases"])

Service = Annotated[LeaseService, Depends(get_lease_service)]


@router.get(
    "",
    response_model=list[LeaseOut],
    summary="List leases (admin: all, tenant: own)",
)
async def list_leases(
    user: TenantOrAdminUser,
    service: Service,
    page: PageDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Tenant name/phone, flat no or building")
    ] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> list[Lease]:
    return await service.search(user, LeaseFilters(q=q, is_active=is_active), page)


@router.get("/{lease_id}", response_model=LeaseOut, summary="Get one lease (tenant: own only)")
async def get_lease(lease_id: int, user: TenantOrAdminUser, service: Service) -> Lease:
    return await service.get(user, lease_id)


@router.post(
    "",
    response_model=LeaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start a lease (admin); marks the flat occupied",
    responses={409: {"description": "Flat already has an active lease"}},
)
async def create_lease(data: LeaseCreate, _: AdminUser, service: Service) -> Lease:
    return await service.create(data)


@router.patch(
    "/{lease_id}",
    response_model=LeaseOut,
    summary="Update or end a lease (admin); keeps the flat status in sync",
)
async def update_lease(lease_id: int, data: LeaseUpdate, _: AdminUser, service: Service) -> Lease:
    return await service.update(lease_id, data)


@router.delete(
    "/{lease_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a lease (admin)"
)
async def delete_lease(lease_id: int, _: AdminUser, service: Service) -> None:
    await service.delete(lease_id)
