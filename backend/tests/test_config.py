"""Settings: fail fast on missing/weak secrets, fix hosting-provider database URLs."""

import pytest

from app.core.config import Settings, SettingsError, get_settings

REQUIRED = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
    "JWT_SECRET_KEY": "x" * 64,
    "LLM_BASE_URL": "https://example.com/v1",
    "LLM_API_KEY": "llm-key",
    "LLM_MODEL": "model",
    "EMBEDDING_BASE_URL": "https://example.com/v1",
    "EMBEDDING_MODEL": "embed",
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**REQUIRED, **overrides})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@dpg-x.render.com/db", "postgresql+asyncpg://u:p@dpg-x.render.com/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        ("postgresql+asyncpg://u:p@db:5432/db", "postgresql+asyncpg://u:p@db:5432/db"),
    ],
)
def test_database_url_is_rewritten_for_asyncpg(given: str, expected: str) -> None:
    assert make(DATABASE_URL=given).DATABASE_URL == expected


def test_weak_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        make(JWT_SECRET_KEY="short")


def test_cors_origins_are_split() -> None:
    settings = make(CORS_ORIGINS="http://localhost:5173, https://baribhara.vercel.app/")
    assert settings.CORS_ORIGINS == ["http://localhost:5173", "https://baribhara.vercel.app"]


def test_embedding_key_falls_back_to_llm_key() -> None:
    assert make().embedding_api_key == "llm-key"
    assert make(EMBEDDING_API_KEY="emb").embedding_api_key == "emb"


def test_missing_secret_stops_startup_without_leaking_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("JWT_SECRET_KEY")
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    try:
        with pytest.raises(SettingsError) as exc_info:
            get_settings()
    finally:
        get_settings.cache_clear()
    message = str(exc_info.value)
    assert "JWT_SECRET_KEY" in message
    assert "llm-key" not in message
