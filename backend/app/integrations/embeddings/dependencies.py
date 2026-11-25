from functools import lru_cache

from app.core.config import get_settings
from app.integrations.embeddings.client import EmbeddingClient


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    settings = get_settings()
    return EmbeddingClient(
        base_url=settings.EMBEDDING_BASE_URL,
        api_key=settings.embedding_api_key,
        model=settings.EMBEDDING_MODEL,
        dim=settings.EMBEDDING_DIM,
    )
