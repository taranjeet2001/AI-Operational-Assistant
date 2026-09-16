from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.knowledge.knowledge_retriever import KnowledgeRetriever


class KnowledgeSearchInput(BaseModel):
    query: str = Field(min_length=3, description="IT support question or problem to search for.")
    limit: int = Field(default=4, ge=1, le=8, description="Maximum number of relevant document sections.")


def build_knowledge_search_tool(retriever: KnowledgeRetriever) -> StructuredTool:
    def search_knowledge_base(query: str, limit: int = 4) -> dict:
        """Search internal IT support documents for troubleshooting or how-to guidance."""
        results = retriever.search(query=query, limit=limit)
        return {"results": [result.__dict__ for result in results]}

    return StructuredTool.from_function(
        func=search_knowledge_base,
        name="knowledge_search",
        description="Search internal IT help documents before answering troubleshooting or policy questions.",
        args_schema=KnowledgeSearchInput,
    )
