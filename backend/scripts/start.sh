#!/bin/sh
# Container entrypoint: migrate, optionally seed/ingest (for hosts without a shell,
# e.g. Render's free tier), then serve.
set -e

alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
    python -m scripts.seed
fi

if [ "${INGEST_ON_START:-false}" = "true" ]; then
    # Unchanged documents are skipped, so this is cheap after the first run.
    python -m scripts.ingest || echo "WARNING: ingest failed; the assistant will answer without documents until it succeeds."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
