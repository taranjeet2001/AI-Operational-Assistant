from dataclasses import dataclass
from functools import lru_cache

from app.knowledge.vector_store_service import VectorStoreService


@dataclass(frozen=True)
class KnowledgeSearchResult:
    content: str
    source_file: str
    relevance_score: float


class KnowledgeRetriever:
    def __init__(self, vector_store: VectorStoreService) -> None:
        self.vector_store = vector_store

    def search(self, query: str, limit: int = 4) -> list[KnowledgeSearchResult]:
        matches = self.vector_store.search(query, limit)
        return [
            KnowledgeSearchResult(
                content=document.page_content,
                source_file=document.metadata["source_file"],
                relevance_score=round(score, 3),
            )
            for document, score in matches
        ]


@lru_cache
def get_knowledge_retriever() -> KnowledgeRetriever:
    """Create one in-memory retriever per API process instead of per request."""
    return KnowledgeRetriever(VectorStoreService())
