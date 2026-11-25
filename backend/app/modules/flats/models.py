from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdCreatedMixin, UpdatedMixin, str_enum

if TYPE_CHECKING:
    from app.modules.buildings.models import Building


class FlatStatus(StrEnum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class Flat(IdCreatedMixin, UpdatedMixin, Base):
    __tablename__ = "flats"
    __table_args__ = (
        UniqueConstraint("building_id", "flat_no"),
        CheckConstraint("floor >= 0", name="floor_non_negative"),
        CheckConstraint("bedrooms BETWEEN 1 AND 10", name="bedrooms_range"),
        CheckConstraint("bathrooms BETWEEN 1 AND 10", name="bathrooms_range"),
        CheckConstraint("size_sqft > 0", name="size_positive"),
        CheckConstraint("monthly_rent >= 0", name="rent_non_negative"),
        CheckConstraint("service_charge >= 0", name="service_charge_non_negative"),
    )

    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    flat_no: Mapped[str] = mapped_column(String(10), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    size_sqft: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_rent: Mapped[int] = mapped_column(Integer, nullable=False)
    service_charge: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[FlatStatus] = mapped_column(
        str_enum(FlatStatus, "flat_status"),
        default=FlatStatus.VACANT,
        server_default=FlatStatus.VACANT.value,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)

    # FlatOut shows building_name and area, so the building is always loaded with the flat.
    building: Mapped["Building"] = relationship(lazy="joined", innerjoin=True)
