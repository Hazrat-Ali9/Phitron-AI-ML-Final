from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import AdminUser, CurrentUser
from app.modules.knowledge.dependencies import get_knowledge_service
from app.modules.knowledge.repositories import ChunkHit, DocumentSummary
from app.modules.knowledge.schemas import KnowledgeDocumentOut, KnowledgeHitOut, KnowledgeSearchIn
from app.modules.knowledge.services import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

Service = Annotated[KnowledgeService, Depends(get_knowledge_service)]


@router.get(
    "/documents",
    response_model=list[KnowledgeDocumentOut],
    summary="Ingested documents with chunk counts (admin)",
)
async def list_documents(_: AdminUser, service: Service) -> list[DocumentSummary]:
    return await service.documents()


@router.post(
    "/search",
    response_model=list[KnowledgeHitOut],
    summary="Semantic search over the building documents ([] when nothing is relevant)",
)
async def search(data: KnowledgeSearchIn, user: CurrentUser, service: Service) -> list[ChunkHit]:
    return await service.search_for(user, data)
