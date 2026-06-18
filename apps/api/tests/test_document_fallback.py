import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import uuid

from app.services.document_fallback import retrieve_document_chunks_fallback

class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        # Return normalized vectors
        if "resume" in text or "query" in text:
            return [1.0] + [0.0] * 767
        return [0.0, 1.0] + [0.0] * 766

@pytest.mark.anyio
async def test_retrieve_document_chunks_fallback_success(tmp_path):
    # Setup mock pool
    pool = AsyncMock()
    doc_uuid = uuid.uuid4()
    storage_file = tmp_path / "resume.txt"
    storage_file.write_text("This is Parth's resume. His CGPA is 9.5.", encoding="utf-8")

    pool.fetch.return_value = [
        {
            "id": doc_uuid,
            "filename": "resume.txt",
            "storage_url": str(storage_file),
        }
    ]

    embedding_service = FakeEmbeddingService()
    
    # Run retrieval
    results = await retrieve_document_chunks_fallback(
        pool=pool,
        embedding_service=embedding_service,
        workspace_id=str(uuid.uuid4()),
        query="Parth's resume query",
        document_ids=[str(doc_uuid)],
        limit=5,
        min_score=0.40
    )

    assert len(results) > 0
    assert results[0]["filename"] == "resume.txt"
    assert "resume" in results[0]["content"].lower()
    assert results[0]["score"] == 1.0
