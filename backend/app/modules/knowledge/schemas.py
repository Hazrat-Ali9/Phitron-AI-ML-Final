from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class KnowledgeSearchIn(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
    top_k: int | None = Field(default=None, ge=1, le=10, description="Defaults to RAG_TOP_K")
    min_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Admin only, for tuning: override RAG_MIN_SCORE (0 shows every score)",
    )


class KnowledgeHitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    title: str
    chunk_index: int
    content: str
    score: float


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_path: str
    embedding_model: str
    chunk_count: int
    updated_at: datetime
