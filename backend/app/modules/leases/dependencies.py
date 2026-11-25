from typing import Annotated

from fastapi import Depends

from app.modules.flats.dependencies import get_flat_repository
from app.modules.flats.repositories import FlatRepository
from app.modules.leases.repositories import LeaseRepository
from app.modules.leases.services import LeaseService
from app.modules.users.dependencies import DbSession, get_user_repository
from app.modules.users.repositories import UserRepository


def get_lease_repository(db: DbSession) -> LeaseRepository:
    return LeaseRepository(db)


def get_lease_service(
    leases: Annotated[LeaseRepository, Depends(get_lease_repository)],
    flats: Annotated[FlatRepository, Depends(get_flat_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> LeaseService:
    return LeaseService(leases, flats, users)
