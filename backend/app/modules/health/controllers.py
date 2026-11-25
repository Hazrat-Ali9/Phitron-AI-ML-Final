from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.modules.health.dependencies import get_health_service
from app.modules.health.schemas import HealthResponse
from app.modules.health.services import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
async def health(
    response: Response, service: Annotated[HealthService, Depends(get_health_service)]
) -> HealthResponse:
    result = await service.check()
    if result.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
