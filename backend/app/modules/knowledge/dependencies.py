from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.embeddings.client import EmbeddingClient
from app.integrations.embeddings.dependencies import get_embedding_client
from app.modules.knowledge.repositories import KnowledgeRepository
from app.modules.knowledge.services import KnowledgeService
from app.modules.users.dependencies import DbSession


def build_knowledge_service(session: AsyncSession, embeddings: EmbeddingClient) -> KnowledgeService:
    settings = get_settings()
    return KnowledgeService(
        KnowledgeRepository(session),
        embeddings,
        top_k=settings.RAG_TOP_K,
        min_score=settings.RAG_MIN_SCORE,
    )


def get_knowledge_service(
    db: DbSession, embeddings: Annotated[EmbeddingClient, Depends(get_embedding_client)]
) -> KnowledgeService:
    return build_knowledge_service(db, embeddings)
