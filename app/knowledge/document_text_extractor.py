from pathlib import Path

from docx import Document as WordDocument
from pypdf import PdfReader


class DocumentTextExtractor:
    """Extracts text from the supported internal knowledge-base file types."""

    supported_extensions = {".pdf", ".docx", ".txt", ".md"}

    def extract(self, file_path: Path) -> str:
        extension = file_path.suffix.lower()
        if extension in {".txt", ".md"}:
            return file_path.read_text(encoding="utf-8")
        if extension == ".pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(file_path)).pages)
        if extension == ".docx":
            return "\n".join(paragraph.text for paragraph in WordDocument(str(file_path)).paragraphs)
        raise ValueError(f"Unsupported knowledge-base file type: {file_path.suffix}")
