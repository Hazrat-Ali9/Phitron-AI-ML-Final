import hashlib
from dataclasses import dataclass
from enum import StrEnum

from app.integrations.embeddings.client import EmbeddingClient
from app.modules.knowledge.chunking import parse_markdown
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.repositories import ChunkHit, DocumentSummary, KnowledgeRepository
from app.modules.knowledge.schemas import KnowledgeSearchIn
from app.modules.users.models import RoleName, User


class IngestOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class IngestResult:
    title: str
    outcome: IngestOutcome
    chunks: int


class KnowledgeService:
    def __init__(
        self,
        repo: KnowledgeRepository,
        embeddings: EmbeddingClient,
        top_k: int,
        min_score: float,
    ) -> None:
        self.repo = repo
        self.embeddings = embeddings
        self.top_k = top_k
        self.min_score = min_score

    async def search(
        self, query: str, top_k: int | None = None, min_score: float | None = None
    ) -> list[ChunkHit]:
        """Chunks relevant to the question, best first. Empty list = nothing relevant."""
        vector = await self.embeddings.embed_query(query)
        hits = await self.repo.nearest_chunks(vector, top_k or self.top_k)
        threshold = self.min_score if min_score is None else min_score
        return [hit for hit in hits if hit.score >= threshold]

    async def search_for(self, user: User, data: KnowledgeSearchIn) -> list[ChunkHit]:
        # Only the owner may lower the threshold (used to tune RAG_MIN_SCORE).
        min_score = data.min_score if user.role_name == RoleName.ADMIN else None
        return await self.search(data.query, top_k=data.top_k, min_score=min_score)

    async def documents(self) -> list[DocumentSummary]:
        return await self.repo.summaries()

    async def ingest(
        self, source_path: str, text: str, fallback_title: str, *, force: bool = False
    ) -> IngestResult:
        """Chunk, embed and store one document in a single transaction (idempotent)."""
        parsed = parse_markdown(text, fallback_title)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        model = self.embeddings.model

        document = await self.repo.get_by_title(parsed.title)
        unchanged = (
            document is not None
            and document.content_hash == content_hash
            and document.embedding_model == model
        )
        if unchanged and not force:
            return IngestResult(parsed.title, IngestOutcome.SKIPPED, 0)

        # Embed first: if the provider fails, nothing in the database has changed.
        vectors = await self.embeddings.embed_documents(parsed.chunks)

        outcome = IngestOutcome.UPDATED
        if document is None:
            outcome = IngestOutcome.CREATED
            document = KnowledgeDocument(
                title=parsed.title,
                source_path=source_path,
                content_hash=content_hash,
                embedding_model=model,
            )
            await self.repo.add(document)
        else:
            await self.repo.update(
                document,
                {
                    "source_path": source_path,
                    "content_hash": content_hash,
                    "embedding_model": model,
                },
            )
        await self.repo.replace_chunks(document, list(zip(parsed.chunks, vectors, strict=True)))
        await self.repo.commit()
        return IngestResult(parsed.title, outcome, len(parsed.chunks))
