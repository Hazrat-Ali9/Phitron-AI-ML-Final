from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.health.repositories import HealthRepository
from app.modules.health.services import HealthService


def get_health_service(db: Annotated[AsyncSession, Depends(get_db)]) -> HealthService:
    return HealthService(HealthRepository(db))
