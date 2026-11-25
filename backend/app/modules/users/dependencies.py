from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.users.repositories import RoleRepository, UserRepository
from app.modules.users.services import UserService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_role_repository(db: DbSession) -> RoleRepository:
    return RoleRepository(db)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)
