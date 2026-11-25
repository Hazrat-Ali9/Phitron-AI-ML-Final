from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select

from app.core.repository import BaseRepository
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument


@dataclass(frozen=True)
class ChunkHit:
    document_id: int
    title: str
    chunk_index: int
    content: str
    score: float  # cosine similarity, 1 = identical direction


@dataclass(frozen=True)
class DocumentSummary:
    id: int
    title: str
    source_path: str
    embedding_model: str
    chunk_count: int
    updated_at: datetime


class KnowledgeRepository(BaseRepository[KnowledgeDocument]):
    model = KnowledgeDocument

    async def get_by_title(self, title: str) -> KnowledgeDocument | None:
        return await self.session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.title == title)
        )

    async def replace_chunks(
        self, document: KnowledgeDocument, chunks: list[tuple[str, list[float]]]
    ) -> None:
        await self.session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id)
        )
        self.session.add_all(
            KnowledgeChunk(document_id=document.id, chunk_index=i, content=text, embedding=vector)
            for i, (text, vector) in enumerate(chunks)
        )
        await self.session.flush()

    async def nearest_chunks(self, query_vector: list[float], limit: int) -> list[ChunkHit]:
        """Closest chunks by cosine distance (uses the HNSW index)."""
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance")
        stmt = (
            select(
                KnowledgeChunk.document_id,
                KnowledgeDocument.title,
                KnowledgeChunk.chunk_index,
                KnowledgeChunk.content,
                distance,
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .order_by(distance)
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return [
            ChunkHit(
                document_id=row.document_id,
                title=row.title,
                chunk_index=row.chunk_index,
                content=row.content,
                score=1.0 - float(row.distance),
            )
            for row in rows
        ]

    async def summaries(self) -> list[DocumentSummary]:
        chunk_count = func.count(KnowledgeChunk.id).label("chunk_count")
        stmt = (
            select(KnowledgeDocument, chunk_count)
            .outerjoin(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .group_by(KnowledgeDocument.id)
            .order_by(KnowledgeDocument.title)
        )
        return [
            DocumentSummary(
                id=doc.id,
                title=doc.title,
                source_path=doc.source_path,
                embedding_model=doc.embedding_model,
                chunk_count=count,
                updated_at=doc.updated_at,
            )
            for doc, count in await self.session.execute(stmt)
        ]
