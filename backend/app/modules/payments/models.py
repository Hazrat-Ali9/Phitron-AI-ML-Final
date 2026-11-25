from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdCreatedMixin, UpdatedMixin, str_enum

if TYPE_CHECKING:
    from app.modules.leases.models import Lease


class PaymentMethod(StrEnum):
    BKASH = "bkash"
    NAGAD = "nagad"
    CASH = "cash"
    BANK = "bank"


class PaymentStatus(StrEnum):
    PAID = "paid"
    PARTIAL = "partial"
    DUE = "due"


class RentPayment(IdCreatedMixin, UpdatedMixin, Base):
    """One row per lease per month: what was due and what has been paid so far."""

    __tablename__ = "rent_payments"
    __table_args__ = (
        UniqueConstraint("lease_id", "month"),
        CheckConstraint("month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'", name="month_format"),
        CheckConstraint("amount_due > 0", name="amount_due_positive"),
        CheckConstraint("amount_paid >= 0", name="amount_paid_non_negative"),
    )

    lease_id: Mapped[int] = mapped_column(
        ForeignKey("leases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    month: Mapped[str] = mapped_column(CHAR(7), index=True, nullable=False)
    amount_due: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_paid: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    method: Mapped[PaymentMethod | None] = mapped_column(str_enum(PaymentMethod, "payment_method"))
    trx_id: Mapped[str | None] = mapped_column(String(30))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Stored (so it can be filtered on) but always computed by PaymentService.
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus, "payment_status"), index=True, nullable=False
    )

    lease: Mapped["Lease"] = relationship(lazy="joined", innerjoin=True)
