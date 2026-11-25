"""Imports every ORM model so `Base.metadata` knows all tables (used by Alembic)."""

from app.core.database import Base
from app.modules.buildings.models import Building
from app.modules.flats.models import Flat
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.leases.models import Lease
from app.modules.maintenance.models import MaintenanceRequest
from app.modules.payments.models import RentPayment
from app.modules.users.models import Role, User

__all__ = [
    "Base",
    "Building",
    "Flat",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "Lease",
    "MaintenanceRequest",
    "RentPayment",
    "Role",
    "User",
]
