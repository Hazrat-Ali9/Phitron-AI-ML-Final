"""Builds the same services the HTTP API uses, for callers outside FastAPI's `Depends`
(the chat tools and the MCP server). One instance per DB session."""

from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.embeddings.client import EmbeddingClient
from app.modules.buildings.repositories import BuildingRepository
from app.modules.buildings.services import BuildingService
from app.modules.flats.repositories import FlatRepository
from app.modules.flats.services import FlatService
from app.modules.knowledge.dependencies import build_knowledge_service
from app.modules.knowledge.services import KnowledgeService
from app.modules.leases.repositories import LeaseRepository
from app.modules.leases.services import LeaseService
from app.modules.maintenance.repositories import MaintenanceRepository
from app.modules.maintenance.services import MaintenanceService
from app.modules.payments.repositories import PaymentRepository
from app.modules.payments.services import PaymentService
from app.modules.users.repositories import UserRepository


class Services:
    def __init__(self, session: AsyncSession, embeddings: EmbeddingClient | None = None) -> None:
        self.session = session
        self.embeddings = embeddings

    @cached_property
    def users_repo(self) -> UserRepository:
        return UserRepository(self.session)

    @cached_property
    def buildings(self) -> BuildingService:
        return BuildingService(BuildingRepository(self.session))

    @cached_property
    def flats(self) -> FlatService:
        return FlatService(
            FlatRepository(self.session),
            BuildingRepository(self.session),
            LeaseRepository(self.session),
            MaintenanceRepository(self.session),
        )

    @cached_property
    def leases(self) -> LeaseService:
        return LeaseService(
            LeaseRepository(self.session), FlatRepository(self.session), self.users_repo
        )

    @cached_property
    def payments(self) -> PaymentService:
        return PaymentService(PaymentRepository(self.session), LeaseRepository(self.session))

    @cached_property
    def knowledge(self) -> KnowledgeService:
        if self.embeddings is None:
            raise RuntimeError("Services was built without an embedding client")
        return build_knowledge_service(self.session, self.embeddings)

    @cached_property
    def maintenance(self) -> MaintenanceService:
        return MaintenanceService(
            MaintenanceRepository(self.session),
            FlatRepository(self.session),
            LeaseRepository(self.session),
            self.users_repo,
        )
