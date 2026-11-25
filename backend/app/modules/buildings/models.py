from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdCreatedMixin, UpdatedMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class Building(IdCreatedMixin, UpdatedMixin, Base):
    __tablename__ = "buildings"
    __table_args__ = (CheckConstraint("total_floors BETWEEN 1 AND 30", name="total_floors_range"),)

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    area: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    total_floors: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    owner: Mapped["User"] = relationship(lazy="raise")
