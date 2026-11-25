"""Chunk, embed and store backend/knowledge/*.md for RAG (idempotent).

Unchanged files (same sha256 and same embedding model) are skipped. Use --force to
re-embed everything, e.g. after changing EMBEDDING_MODEL.

Run from backend/:  uv run python -m scripts.ingest [--force]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app import models  # noqa: F401  (register all models)
from app.core.database import SessionLocal, engine
from app.integrations.embeddings.client import EmbeddingUnavailableError
from app.integrations.embeddings.dependencies import get_embedding_client
from app.modules.knowledge.dependencies import build_knowledge_service
from app.modules.knowledge.services import IngestOutcome

BACKEND_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BACKEND_DIR / "knowledge"


async def ingest(directory: Path, force: bool) -> None:
    files = sorted(directory.glob("*.md"))
    if not files:
        print(f"No .md files in {directory}")
        return

    embeddings = get_embedding_client()
    print(f"Embedding model: {embeddings.model} ({embeddings.dim} dims)")
    counts = {outcome: 0 for outcome in IngestOutcome}
    chunks_written = 0

    for path in files:
        # One session (= one transaction) per document: a failure keeps earlier documents.
        async with SessionLocal() as session:
            service = build_knowledge_service(session, embeddings)
            result = await service.ingest(
                source_path=str(path.relative_to(BACKEND_DIR)),
                text=path.read_text(encoding="utf-8"),
                fallback_title=path.stem.replace("-", " ").title(),
                force=force,
            )
        counts[result.outcome] += 1
        chunks_written += result.chunks
        detail = f"{result.chunks} chunks" if result.chunks else "unchanged"
        print(f"  {result.outcome.value:<8} {result.title}  ({detail})")

    await engine.dispose()
    print(
        f"\nDone: {counts[IngestOutcome.CREATED]} created, {counts[IngestOutcome.UPDATED]} "
        f"updated, {counts[IngestOutcome.SKIPPED]} skipped; {chunks_written} chunks written."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-embed unchanged files too")
    parser.add_argument("--dir", type=Path, default=KNOWLEDGE_DIR, help="folder with .md files")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    try:
        asyncio.run(ingest(args.dir, args.force))
    except EmbeddingUnavailableError:
        sys.exit(
            "\nIngest stopped: the embedding API call failed (see the warning above).\n"
            "Check EMBEDDING_BASE_URL / EMBEDDING_MODEL and the API key "
            "(EMBEDDING_API_KEY, or LLM_API_KEY when it is empty) in .env."
        )


if __name__ == "__main__":
    main()
