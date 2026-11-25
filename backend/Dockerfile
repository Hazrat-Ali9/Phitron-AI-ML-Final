# BariBhara API: FastAPI + uv, runs migrations on start.
FROM python:3.12-slim

# uv binary from the official image (pinned minor version)
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    # `uv run` inside the container must not try to re-sync (e.g. install dev deps)
    UV_NO_SYNC=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production

WORKDIR /app

# Dependencies first, so this layer is cached until pyproject.toml / uv.lock change
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY knowledge ./knowledge

# Non-root at runtime. The app only reads /app, so no chown (it would duplicate the venv layer).
RUN useradd --create-home --uid 10001 baribhara
USER baribhara

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/v1/health', timeout=4)"

# Migrate, optionally seed/ingest (SEED_ON_START / INGEST_ON_START), then serve on
# ${PORT:-8000} (Render sets PORT).
CMD ["sh", "scripts/start.sh"]
