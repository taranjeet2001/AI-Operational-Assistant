from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


class EmbeddingService:
    """Creates embeddings consistently for ingestion and retrieval."""

    def __init__(self) -> None:
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )
