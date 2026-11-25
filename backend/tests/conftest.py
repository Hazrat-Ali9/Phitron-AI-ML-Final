"""Test setup: a fresh `<db>_test` database, migrated with Alembic, plus helpers to make users.

Needs the docker compose `db` service running (or any Postgres with pgvector).
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

# Point the app at a separate database *before* any app module reads the settings.
from app.core.config import Settings  # noqa: E402  (only the class, settings not built yet)

_base_url = make_url(Settings().DATABASE_URL)  # type: ignore[call-arg]
TEST_DB_NAME = f"{_base_url.database}_test"
os.environ["DATABASE_URL"] = _base_url.set(database=TEST_DB_NAME).render_as_string(
    hide_password=False
)

import asyncpg  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


async def _recreate_database() -> None:
    admin_url = _base_url.set(drivername="postgresql", database="postgres")
    conn = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    asyncio.run(_recreate_database())
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture(scope="session")
async def roles(database: None) -> None:
    from app.core.database import SessionLocal
    from app.modules.users.models import Role, RoleName

    async with SessionLocal() as session:
        session.add_all([Role(name=name.value) for name in RoleName])
        await session.commit()


@pytest.fixture(scope="session")
async def client(roles: None) -> AsyncIterator[AsyncClient]:
    from app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c


@dataclass
class AuthedUser:
    id: int
    email: str
    password: str
    role: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


MakeUser = Callable[..., Awaitable[AuthedUser]]


@pytest.fixture(scope="session")
async def make_user(roles: None) -> MakeUser:
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.core.security import create_access_token, hash_password
    from app.modules.users.models import Role, User

    async def _make(role: str = "tenant", full_name: str = "Test User") -> AuthedUser:
        email = f"{role}-{uuid.uuid4().hex[:8]}@example.com"
        password = "password123"
        async with SessionLocal() as session:
            role_row = await session.scalar(select(Role).where(Role.name == role))
            user = User(
                full_name=full_name,
                email=email,
                phone=None,
                password_hash=hash_password(password),
                role=role_row,
            )
            session.add(user)
            await session.commit()
            token = create_access_token(user.id).token
            return AuthedUser(user.id, email, password, role, token)

    return _make
