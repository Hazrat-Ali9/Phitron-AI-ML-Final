from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.pagination import PageDep
from app.modules.auth.dependencies import require_roles
from app.modules.users.dependencies import get_user_service
from app.modules.users.models import RoleName, User
from app.modules.users.schemas import UserOut
from app.modules.users.services import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut], summary="List users (admin, staff)")
async def list_users(
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.STAFF))],
    service: Annotated[UserService, Depends(get_user_service)],
    page: PageDep,
    role: Annotated[RoleName | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100, description="Name, email or phone")] = None,
) -> list[User]:
    return await service.list_users(page, role=role, q=q)
