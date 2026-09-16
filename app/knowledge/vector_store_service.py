from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import get_settings
from app.knowledge.embedding_service import EmbeddingService


class VectorStoreService:
    """Persistent FAISS index operations for internal support documents."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        settings = get_settings()
        settings.faiss_index_directory.mkdir(parents=True, exist_ok=True)
        embedding_service = embedding_service or EmbeddingService()
        self.index_directory = settings.faiss_index_directory
        self.embeddings = embedding_service.embeddings
        self._store: FAISS | None = None
        self._loaded_index_mtime: int | None = None

    def replace_document(self, document_id: str, chunks: list[Document]) -> None:
        store = self._load_store()
        if store is None:
            if chunks:
                FAISS.from_documents(chunks, self.embeddings).save_local(str(self.index_directory))
            return

        existing_ids = [
            faiss_id
            for faiss_id, docstore_id in store.index_to_docstore_id.items()
            if store.docstore.search(docstore_id).metadata.get("document_id") == document_id
        ]
        if existing_ids:
            store.delete(existing_ids)
        if chunks:
            store.add_documents(chunks)
        store.save_local(str(self.index_directory))

    def search(self, query: str, limit: int) -> list[tuple[Document, float]]:
        store = self._load_store()
        return store.similarity_search_with_relevance_scores(query, k=limit) if store else []

    def _load_store(self) -> FAISS | None:
        index_path = self.index_directory / "index.faiss"
        if not index_path.exists():
            self._store = None
            self._loaded_index_mtime = None
            return None
        index_mtime = index_path.stat().st_mtime_ns
        if self._store is not None and self._loaded_index_mtime == index_mtime:
            return self._store
        # FAISS persists its docstore metadata with pickle. This directory is written only
        # by this application and must not be replaced with an untrusted index.
        self._store = FAISS.load_local(
            str(self.index_directory),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        self._loaded_index_mtime = index_mtime
        return self._store
