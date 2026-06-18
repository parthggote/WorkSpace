"""Document ingestion helpers for future upload and embedding workflows.

This module is deliberately framework-light so FastAPI routes, background tasks,
or Celery workers can call the same ingestion pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable, Iterable, Protocol
from uuid import UUID, uuid4


DEFAULT_CHUNK_CHARS = 3200
DEFAULT_OVERLAP_CHARS = 500
MIN_CHUNK_CHARS = 600


class EmbeddingService(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


class DocumentChunkStore(Protocol):
    def save_document(self, record: "DocumentRecord") -> None:
        """Persist document metadata."""

    def save_chunks(self, chunks: list["DocumentChunk"]) -> None:
        """Persist document chunks and optional embeddings."""


@dataclass(frozen=True)
class DocumentRecord:
    id: UUID
    workspace_id: UUID
    uploaded_by: UUID | None
    filename: str
    file_type: str
    status: str
    checksum: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    id: UUID
    document_id: UUID
    workspace_id: UUID
    chunk_index: int
    text: str
    token_estimate: int
    checksum: str
    embedding: list[float] | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionResult:
    document: DocumentRecord
    chunks: list[DocumentChunk]


def estimate_tokens(text: str) -> int:
    """Cheap token estimate suitable for budgeting before model-specific counts."""
    return max(1, len(text) // 4)


def clean_text_for_postgres(text: str) -> str:
    """Remove characters PostgreSQL text columns cannot store."""
    if not text:
        return ""
    return text.replace("\x00", "")


def normalize_text(text: str) -> str:
    text = clean_text_for_postgres(text)
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    collapsed: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        collapsed.append(line)
        previous_blank = is_blank
    return "\n".join(collapsed).strip()


def chunk_text(
    text: str,
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
    min_chunk_chars: int = MIN_CHUNK_CHARS,
) -> list[str]:
    """Split text into stable overlapping chunks without cutting words when possible."""
    clean_text = normalize_text(text)
    if not clean_text:
        return []
    if len(clean_text) <= chunk_chars:
        return [clean_text]

    chunks: list[str] = []
    start = 0
    while start < len(clean_text):
        end = min(len(clean_text), start + chunk_chars)
        if end < len(clean_text):
            boundary = max(clean_text.rfind("\n", start, end), clean_text.rfind(". ", start, end))
            if boundary > start + min_chunk_chars:
                end = boundary + 1

        chunk = clean_text[start:end].strip()
        if len(chunk) >= min_chunk_chars or not chunks:
            chunks.append(chunk)
        elif chunks:
            chunks[-1] = f"{chunks[-1]}\n{chunk}".strip()

        if end >= len(clean_text):
            break
        start = max(end - overlap_chars, start + 1)

    return chunks


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text from common upload types with optional dependency support."""
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json", ".log"}:
        return content.decode("utf-8", errors="replace")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
            from io import BytesIO

            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # pragma: no cover - depends on optional parser
            raise ValueError("PDF text extraction requires a readable PDF and pypdf") from exc

    if suffix == ".docx":
        try:
            import docx  # type: ignore
            from io import BytesIO

            document = docx.Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:  # pragma: no cover - depends on optional parser
            raise ValueError("DOCX text extraction requires python-docx") from exc

    raise ValueError(f"Unsupported document type: {suffix or 'unknown'}")


class DocumentIngestionService:
    """Prepare uploaded documents for pgvector-backed retrieval."""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        chunk_store: DocumentChunkStore | None = None,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._embedding_service = embedding_service
        self._chunk_store = chunk_store
        self._id_factory = id_factory

    def ingest_bytes(
        self,
        *,
        workspace_id: UUID,
        filename: str,
        content: bytes,
        uploaded_by: UUID | None = None,
        metadata: dict[str, str] | None = None,
        embed: bool = True,
    ) -> IngestionResult:
        text = extract_text_from_bytes(content, filename)
        return self.ingest_text(
            workspace_id=workspace_id,
            filename=filename,
            text=text,
            uploaded_by=uploaded_by,
            metadata=metadata,
            embed=embed,
            checksum=sha256(content).hexdigest(),
        )

    def ingest_text(
        self,
        *,
        workspace_id: UUID,
        filename: str,
        text: str,
        uploaded_by: UUID | None = None,
        metadata: dict[str, str] | None = None,
        embed: bool = True,
        checksum: str | None = None,
    ) -> IngestionResult:
        chunks_text = chunk_text(text)
        document = DocumentRecord(
            id=self._id_factory(),
            workspace_id=workspace_id,
            uploaded_by=uploaded_by,
            filename=filename,
            file_type=Path(filename).suffix.lower().lstrip(".") or "text",
            status="ready" if chunks_text else "failed",
            checksum=checksum or sha256(text.encode("utf-8")).hexdigest(),
            metadata=metadata or {},
        )

        embeddings = self._embed_chunks(chunks_text) if embed and chunks_text else [None] * len(chunks_text)
        chunks = [
            DocumentChunk(
                id=self._id_factory(),
                document_id=document.id,
                workspace_id=workspace_id,
                chunk_index=index,
                text=chunk,
                token_estimate=estimate_tokens(chunk),
                checksum=sha256(chunk.encode("utf-8")).hexdigest(),
                embedding=embeddings[index],
                metadata={"filename": filename, **(metadata or {})},
            )
            for index, chunk in enumerate(chunks_text)
        ]

        if self._chunk_store is not None:
            self._chunk_store.save_document(document)
            if chunks:
                self._chunk_store.save_chunks(chunks)

        return IngestionResult(document=document, chunks=chunks)

    def _embed_chunks(self, chunks: Iterable[str]) -> list[list[float] | None]:
        chunk_list = list(chunks)
        if self._embedding_service is None:
            return [None] * len(chunk_list)
        return list(self._embedding_service.embed_texts(chunk_list))
