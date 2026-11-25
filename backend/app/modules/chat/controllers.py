from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import CurrentUser
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.chat.services import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask the BariBhara assistant (multi-turn: send the previous turns in history)",
    responses={503: {"description": "LLM provider unavailable"}},
)
async def chat(
    request: ChatRequest,
    user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    return await service.chat(user, request)
