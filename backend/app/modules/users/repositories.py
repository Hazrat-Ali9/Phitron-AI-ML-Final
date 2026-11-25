from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page
from app.core.query import contains_pattern
from app.modules.users.models import Role, User


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, name: str) -> Role | None:
        return await self.session.scalar(select(Role).where(Role.name == name))


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        # Emails are stored lower-case (see RegisterIn), so the unique index is used.
        return await self.session.scalar(select(User).where(User.email == email.lower()))

    async def email_exists(self, email: str) -> bool:
        stmt = select(User.id).where(User.email == email.lower())
        return await self.session.scalar(stmt) is not None

    async def search(self, page: Page, role: str | None = None, q: str | None = None) -> list[User]:
        stmt = select(User).join(User.role)
        if role:
            stmt = stmt.where(Role.name == role)
        if q:
            pattern = contains_pattern(q)
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.phone.ilike(pattern),
                )
            )
        stmt = stmt.order_by(User.full_name).limit(page.limit).offset(page.offset)
        return list(await self.session.scalars(stmt))

    async def first_with_role(self, role: str) -> User | None:
        stmt = (
            select(User)
            .join(User.role)
            .where(Role.name == role, User.is_active.is_(True))
            .order_by(User.id)
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def commit(self) -> None:
        await self.session.commit()
