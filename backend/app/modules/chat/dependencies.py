from typing import Annotated

from fastapi import Depends

from app.integrations.embeddings.client import EmbeddingClient
from app.integrations.embeddings.dependencies import get_embedding_client
from app.integrations.llm.client import LLMClient
from app.integrations.llm.dependencies import get_llm_client
from app.modules.chat.services import ChatService
from app.modules.users.dependencies import DbSession


def get_chat_service(
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    embeddings: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    db: DbSession,
) -> ChatService:
    return ChatService(llm, db, embeddings)
