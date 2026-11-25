from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut
from app.modules.users.models import RoleName, User
from app.modules.users.repositories import RoleRepository, UserRepository

LOGIN_FAILED = "Incorrect email or password"


class AuthService:
    def __init__(self, users: UserRepository, roles: RoleRepository) -> None:
        self.users = users
        self.roles = roles

    async def register(self, data: RegisterIn) -> User:
        if await self.users.email_exists(data.email):
            raise ConflictError("An account with this email already exists")

        # Public registration always creates a tenant. Admin/staff come from the seed script.
        tenant_role = await self.roles.get_by_name(RoleName.TENANT)
        if tenant_role is None:
            raise RuntimeError("Role 'tenant' is missing. Run the seed script first.")

        user = User(
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=tenant_role,
        )
        await self.users.add(user)
        await self.users.commit()
        return user

    async def login(self, data: LoginIn) -> TokenOut:
        user = await self.users.get_by_email(data.email)
        # verify_password runs a dummy hash when the user is missing, so both failure
        # cases take similar time and return the very same message.
        password_ok = verify_password(data.password, user.password_hash if user else None)
        if user is None or not password_ok or not user.is_active:
            raise UnauthorizedError(LOGIN_FAILED)

        token = create_access_token(user.id)
        return TokenOut(access_token=token.token, expires_in=token.expires_in)

    async def user_from_token(self, token: str) -> User:
        user_id = decode_access_token(token)
        # The role is read from the database on every request, never trusted from the token.
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return user
