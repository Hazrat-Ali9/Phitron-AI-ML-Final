from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdCreatedMixin, UpdatedMixin


class RoleName(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"
    TENANT = "tenant"


class Role(IdCreatedMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)


class User(IdCreatedMixin, UpdatedMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    # Always needed (permission checks, UserOut.role), so it is loaded in the same query.
    role: Mapped[Role] = relationship(lazy="joined", innerjoin=True)

    @property
    def role_name(self) -> str:
        return self.role.name
