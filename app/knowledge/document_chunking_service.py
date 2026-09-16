from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunkingService:
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150) -> None:
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split(self, content: str, metadata: dict[str, str]) -> list[Document]:
        return self.splitter.create_documents([content], metadatas=[metadata])
