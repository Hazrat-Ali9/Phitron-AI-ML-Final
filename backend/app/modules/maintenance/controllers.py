from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import PageDep
from app.modules.auth.dependencies import AdminUser, CurrentUser, StaffOrAdminUser
from app.modules.maintenance.dependencies import get_maintenance_service
from app.modules.maintenance.models import (
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.modules.maintenance.repositories import MaintenanceFilters
from app.modules.maintenance.schemas import MaintenanceCreate, MaintenanceOut, MaintenanceUpdate
from app.modules.maintenance.services import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

Service = Annotated[MaintenanceService, Depends(get_maintenance_service)]


@router.get(
    "",
    response_model=list[MaintenanceOut],
    summary="Repair requests, newest first (tenant: own)",
)
async def list_requests(
    user: CurrentUser,
    service: Service,
    page: PageDep,
    status: Annotated[MaintenanceStatus | None, Query()] = None,
    category: Annotated[MaintenanceCategory | None, Query()] = None,
    priority: Annotated[MaintenancePriority | None, Query()] = None,
    flat_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[MaintenanceRequest]:
    filters = MaintenanceFilters(
        status=status, category=category, priority=priority, flat_id=flat_id
    )
    return await service.search(user, filters, page)


@router.get("/{request_id}", response_model=MaintenanceOut, summary="Get one repair request")
async def get_request(request_id: int, user: CurrentUser, service: Service) -> MaintenanceRequest:
    return await service.get(user, request_id)


@router.post(
    "",
    response_model=MaintenanceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Report a repair (tenant: for their own flat)",
    responses={403: {"description": "Tenant without an active lease"}},
)
async def create_request(
    data: MaintenanceCreate, user: CurrentUser, service: Service
) -> MaintenanceRequest:
    return await service.create(user, data)


@router.patch(
    "/{request_id}",
    response_model=MaintenanceOut,
    summary="Update status / priority / assignee (admin, staff)",
)
async def update_request(
    request_id: int, data: MaintenanceUpdate, _: StaffOrAdminUser, service: Service
) -> MaintenanceRequest:
    return await service.update(request_id, data)


@router.delete(
    "/{request_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a request (admin)"
)
async def delete_request(request_id: int, _: AdminUser, service: Service) -> None:
    await service.delete(request_id)
