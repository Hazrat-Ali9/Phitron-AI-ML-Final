import logging

from app.modules.health.repositories import HealthRepository
from app.modules.health.schemas import HealthResponse

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, repo: HealthRepository) -> None:
        self.repo = repo

    async def check(self) -> HealthResponse:
        try:
            await self.repo.ping()
        except Exception:
            logger.exception("Database health check failed")
            return HealthResponse(status="degraded", database="error")
        return HealthResponse(status="ok", database="ok")
