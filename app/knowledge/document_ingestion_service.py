import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import KnowledgeDocument
from app.knowledge.document_chunking_service import DocumentChunkingService
from app.knowledge.document_text_extractor import DocumentTextExtractor
from app.knowledge.vector_store_service import VectorStoreService


class DocumentIngestionService:
    """Indexes changed support documents and leaves already indexed files untouched."""

    def __init__(
        self,
        session: Session,
        extractor: DocumentTextExtractor,
        chunker: DocumentChunkingService,
        vector_store: VectorStoreService,
    ) -> None:
        self.session = session
        self.extractor = extractor
        self.chunker = chunker
        self.vector_store = vector_store

    def ingest_directory(self, directory: Path) -> int:
        indexed_count = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.extractor.supported_extensions:
                indexed_count += self._ingest_file(file_path)
        return indexed_count

    def _ingest_file(self, file_path: Path) -> int:
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        document = self.session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.file_name == file_path.name)
        )
        if document and document.content_hash == content_hash:
            return 0

        if document is None:
            document = KnowledgeDocument(
                file_name=file_path.name,
                file_path=str(file_path),
                content_hash=content_hash,
            )
            self.session.add(document)
            self.session.flush()
        else:
            document.file_path = str(file_path)
            document.content_hash = content_hash

        content = self.extractor.extract(file_path).strip()
        chunks = self.chunker.split(
            content,
            {"document_id": document.id, "source_file": file_path.name},
        ) if content else []
        self.vector_store.replace_document(document.id, chunks)
        self.session.commit()
        return 1
