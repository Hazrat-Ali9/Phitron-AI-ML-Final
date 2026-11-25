from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdCreatedMixin, UpdatedMixin, str_enum

if TYPE_CHECKING:
    from app.modules.flats.models import Flat
    from app.modules.users.models import User


class MaintenanceCategory(StrEnum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    GAS = "gas"
    LIFT = "lift"
    PAINTING = "painting"
    OTHER = "other"


class MaintenancePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MaintenanceStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class MaintenanceRequest(IdCreatedMixin, UpdatedMixin, Base):
    __tablename__ = "maintenance_requests"

    flat_id: Mapped[int] = mapped_column(
        ForeignKey("flats.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    reported_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[MaintenanceCategory] = mapped_column(
        str_enum(MaintenanceCategory, "maintenance_category"), nullable=False
    )
    priority: Mapped[MaintenancePriority] = mapped_column(
        str_enum(MaintenancePriority, "maintenance_priority"),
        default=MaintenancePriority.MEDIUM,
        server_default=MaintenancePriority.MEDIUM.value,
        nullable=False,
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        str_enum(MaintenanceStatus, "maintenance_status"),
        default=MaintenanceStatus.OPEN,
        server_default=MaintenanceStatus.OPEN.value,
        index=True,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    flat: Mapped["Flat"] = relationship(lazy="joined", innerjoin=True)
    reported_by: Mapped["User"] = relationship(
        foreign_keys=[reported_by_id], lazy="joined", innerjoin=True
    )
    assigned_to: Mapped["User | None"] = relationship(foreign_keys=[assigned_to_id], lazy="joined")
