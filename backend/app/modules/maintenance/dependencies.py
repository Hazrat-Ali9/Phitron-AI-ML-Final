from typing import Annotated

from fastapi import Depends

from app.modules.flats.dependencies import get_flat_repository
from app.modules.flats.repositories import FlatRepository
from app.modules.leases.dependencies import get_lease_repository
from app.modules.leases.repositories import LeaseRepository
from app.modules.maintenance.repositories import MaintenanceRepository
from app.modules.maintenance.services import MaintenanceService
from app.modules.users.dependencies import DbSession, get_user_repository
from app.modules.users.repositories import UserRepository


def get_maintenance_repository(db: DbSession) -> MaintenanceRepository:
    return MaintenanceRepository(db)


def get_maintenance_service(
    requests: Annotated[MaintenanceRepository, Depends(get_maintenance_repository)],
    flats: Annotated[FlatRepository, Depends(get_flat_repository)],
    leases: Annotated[LeaseRepository, Depends(get_lease_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> MaintenanceService:
    return MaintenanceService(requests, flats, leases, users)
