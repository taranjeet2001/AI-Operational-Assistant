from fastapi import APIRouter, Query

from app.api.schemas import KnowledgeSearchResponse
from app.knowledge.knowledge_retriever import get_knowledge_retriever

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=list[KnowledgeSearchResponse])
def search_knowledge_base(query: str = Query(min_length=3), limit: int = Query(default=4, ge=1, le=8)):
    results = get_knowledge_retriever().search(query, limit)
    return [KnowledgeSearchResponse(**result.__dict__) for result in results]
