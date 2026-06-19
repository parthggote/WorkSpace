import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.document_retrieval import (
    is_document_focused_query,
    is_document_summary_query,
    retrieve_document_chunks,
)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


@pytest.mark.anyio
async def test_summary_query_uses_ordered_document_chunks_without_similarity_gate():
    pool = AsyncMock()
    doc_id = uuid.uuid4()
    pool.fetch.return_value = [
        {
            "content": "Architecture decisions include Supabase, Redis, Celery, and Tavily.",
            "document_id": doc_id,
            "chunk_index": 0,
            "filename": "ARCHITECTURE_DECISIONS.pdf",
        }
    ]

    chunks = await retrieve_document_chunks(
        pool,
        FakeEmbeddingService(),
        workspace_id=str(uuid.uuid4()),
        query="summarize this document",
        document_ids=[str(doc_id)],
        force_ordered_context=True,
    )

    assert len(chunks) == 1
    assert chunks[0]["filename"] == "ARCHITECTURE_DECISIONS.pdf"
    assert chunks[0]["retrieval_reason"] == "ordered_document_context"
    assert "Supabase" in chunks[0]["content"]


def test_document_query_detection_for_attached_file_prompts():
    doc_ids = [str(uuid.uuid4())]

    assert is_document_focused_query("summarize this document", doc_ids)
    assert is_document_summary_query("summarize this document", doc_ids)
    assert not is_document_focused_query("what did we discuss yesterday", doc_ids)
