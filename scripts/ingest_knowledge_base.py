from app.config import get_settings
from app.database.database import SessionLocal, create_database_tables
from app.knowledge.document_chunking_service import DocumentChunkingService
from app.knowledge.document_ingestion_service import DocumentIngestionService
from app.knowledge.document_text_extractor import DocumentTextExtractor
from app.knowledge.vector_store_service import VectorStoreService


def main() -> None:
    settings = get_settings()
    settings.knowledge_base_directory.mkdir(parents=True, exist_ok=True)
    create_database_tables()
    with SessionLocal() as session:
        service = DocumentIngestionService(
            session=session,
            extractor=DocumentTextExtractor(),
            chunker=DocumentChunkingService(),
            vector_store=VectorStoreService(),
        )
        indexed_count = service.ingest_directory(settings.knowledge_base_directory)
    print(f"Indexed {indexed_count} knowledge-base document(s).")


if __name__ == "__main__":
    main()
