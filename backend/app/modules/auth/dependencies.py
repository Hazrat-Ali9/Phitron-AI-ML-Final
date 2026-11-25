from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.modules.auth.services import AuthService
from app.modules.users.dependencies import get_role_repository, get_user_repository
from app.modules.users.models import RoleName, User
from app.modules.users.repositories import RoleRepository, UserRepository

# HTTPBearer gives Swagger's "Authorize" button a single box to paste the token into.
# auto_error=False so a missing header goes through our own 401 (with WWW-Authenticate).
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the access_token from POST /api/v1/auth/login",
)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    roles: Annotated[RoleRepository, Depends(get_role_repository)],
) -> AuthService:
    return AuthService(users, roles)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Not authenticated")
    return await service.user_from_token(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: RoleName) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: `Depends(require_roles(RoleName.ADMIN))` → 403 for other roles."""
    allowed_names = {role.value for role in allowed}

    async def checker(user: CurrentUser) -> User:
        if user.role_name not in allowed_names:
            raise ForbiddenError("You do not have permission to do this")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(RoleName.ADMIN))]
StaffOrAdminUser = Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.STAFF))]
TenantOrAdminUser = Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.TENANT))]
