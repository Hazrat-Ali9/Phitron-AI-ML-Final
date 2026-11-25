from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdCreatedMixin, UpdatedMixin

if TYPE_CHECKING:
    from app.modules.flats.models import Flat
    from app.modules.users.models import User


class Lease(IdCreatedMixin, UpdatedMixin, Base):
    __tablename__ = "leases"
    __table_args__ = (
        # One active lease per flat. Partial unique index; the service checks first so the
        # user gets a friendly 409, and this index makes it impossible even under a race.
        Index(
            "uq_leases_active_flat",
            "flat_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_after_start"),
        CheckConstraint("monthly_rent >= 0", name="rent_non_negative"),
        CheckConstraint("advance_amount >= 0", name="advance_non_negative"),
        CheckConstraint("family_members BETWEEN 1 AND 20", name="family_members_range"),
        CheckConstraint(
            "nid_number ~ '^[0-9]+$' AND length(nid_number) IN (10, 13, 17)",
            name="nid_format",
        ),
    )

    flat_id: Mapped[int] = mapped_column(
        ForeignKey("flats.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    monthly_rent: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Agreed rent + service charge, whole taka"
    )
    advance_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nid_number: Mapped[str] = mapped_column(String(17), nullable=False)
    family_members: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    flat: Mapped["Flat"] = relationship(lazy="joined", innerjoin=True)
    tenant: Mapped["User"] = relationship(lazy="joined", innerjoin=True)
