"""Application settings, loaded from environment variables / `.env`.

Required settings have no default. If one is missing, building `Settings()`
raises a validation error, so the app refuses to start.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Look for .env in backend/ first, then in the repo root (used by docker compose).
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES = (_BACKEND_DIR.parent / ".env", _BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_ENV: Literal["development", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str

    # Auth
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)

    # CORS (comma separated in .env)
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    # LLM (any OpenAI-compatible endpoint)
    LLM_BASE_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str

    # Embeddings (any OpenAI-compatible /embeddings endpoint; Gemini by default)
    EMBEDDING_BASE_URL: str
    EMBEDDING_API_KEY: str | None = None  # empty -> reuse LLM_API_KEY (same Gemini key)
    EMBEDDING_MODEL: str
    # Must match the vector(...) column created by migration 0004. Changing it needs a new
    # migration and a re-ingest: vectors from different models/sizes must never be mixed.
    EMBEDDING_DIM: int = Field(default=768, gt=0, le=2000)

    # RAG
    RAG_TOP_K: int = Field(default=4, gt=0, le=20)
    RAG_MIN_SCORE: float = Field(default=0.65, ge=0.0, le=1.0)

    # MCP
    MCP_API_KEY: str | None = None

    @field_validator("DATABASE_URL")
    @classmethod
    def use_asyncpg_driver(cls, value: str) -> str:
        # Render (and most hosts) hand out postgres:// or postgresql:// URLs.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                value = "postgresql+asyncpg://" + value.removeprefix(prefix)
                break
        # asyncpg calls libpq's `sslmode` parameter `ssl` (external Render URLs need SSL).
        return re.sub(r"([?&])sslmode=", r"\1ssl=", value)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip().rstrip("/") for o in value.split(",") if o.strip()]
        return value

    @field_validator("MCP_API_KEY", "EMBEDDING_API_KEY", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        return value or None

    @property
    def embedding_api_key(self) -> str:
        return self.EMBEDDING_API_KEY or self.LLM_API_KEY

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


class SettingsError(RuntimeError):
    """Raised at startup when required settings are missing or invalid."""


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        # Report only field names and reasons. The default pydantic message echoes
        # every input value, which would print secrets such as LLM_API_KEY to the logs.
        problems = "\n".join(
            f"  - {'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise SettingsError(
            f"Invalid configuration, the app cannot start. Check your .env:\n{problems}"
        ) from None
