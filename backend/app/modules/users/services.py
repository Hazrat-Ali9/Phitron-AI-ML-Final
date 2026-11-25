from app.core.pagination import Page
from app.modules.users.models import RoleName, User
from app.modules.users.repositories import UserRepository


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def list_users(
        self, page: Page, role: RoleName | None = None, q: str | None = None
    ) -> list[User]:
        return await self.users.search(page, role=role.value if role else None, q=q)
