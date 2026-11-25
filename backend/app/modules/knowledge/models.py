from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.database import Base, IdCreatedMixin, UpdatedMixin

EMBEDDING_DIM = get_settings().EMBEDDING_DIM


class KnowledgeDocument(IdCreatedMixin, UpdatedMixin, Base):
    """One source file from backend/knowledge/."""

    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    source_path: Mapped[str] = mapped_column(String(255), nullable=False)
    # sha256 of the file: unchanged files are skipped on the next ingest.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Which model made the vectors. A different model means everything must be re-embedded.
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(IdCreatedMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        # Approximate nearest-neighbour index for cosine distance (the `<=>` operator).
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks", lazy="joined")
