from functools import lru_cache

from app.core.config import get_settings
from app.integrations.llm.client import LLMClient


@lru_cache
def get_llm_client() -> LLMClient:
    """One shared client (it keeps an HTTP connection pool). Override in tests."""
    settings = get_settings()
    return LLMClient(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
    )
