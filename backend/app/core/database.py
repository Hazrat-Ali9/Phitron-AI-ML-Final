"""Async SQLAlchemy engine, session factory, declarative Base and the `get_db` dependency."""

from collections.abc import AsyncIterator
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

# Predictable constraint names, so Alembic migrations can drop/alter them later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdCreatedMixin:
    """`id` primary key + `created_at`, shared by every table."""

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UpdatedMixin:
    # eager_defaults: read server-generated values (updated_at) back with RETURNING after
    # an UPDATE, instead of leaving them expired (an expired attribute would need lazy IO).
    __mapper_args__ = {"eager_defaults": True}

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Store a StrEnum as varchar + CHECK constraint (easier to migrate than a native PG enum).

    `values_callable` stores the lower-case values ('vacant'), not the member names ('VACANT').
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )


settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

# expire_on_commit=False: objects stay usable after commit (no implicit lazy IO in async code).
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """One session per request. Services commit explicitly; anything uncommitted is rolled back."""
    async with SessionLocal() as session:
        yield session
