import os
import uuid
from pathlib import Path
from typing import Any

from app.services.document_ingestion import extract_text_from_bytes, chunk_text
from app.services.embeddings import EmbeddingService

async def retrieve_document_chunks_fallback(
    pool,
    embedding_service: EmbeddingService,
    workspace_id: str,
    query: str,
    document_ids: list[str],
    limit: int = 10,
    min_score: float = 0.40
) -> list[dict]:
    if not document_ids:
        return []

    # Convert document_ids to UUIDs for query
    uuid_ids = []
    for d_id in document_ids:
        try:
            uuid_ids.append(uuid.UUID(str(d_id)))
        except ValueError:
            pass

    if not uuid_ids:
        return []

    rows = await pool.fetch(
        """
        SELECT id, filename, storage_url
        FROM documents
        WHERE id = ANY($1::uuid[])
          AND workspace_id = $2
        """,
        uuid_ids,
        workspace_id,
    )

    if not rows:
        return []

    query_vector = embedding_service.embed(query)
    results = []

    # Determine potential base paths to find the uploaded file
    api_dir = Path(__file__).resolve().parents[2]

    for row in rows:
        storage_url = row["storage_url"]
        filename = row["filename"]
        doc_id = str(row["id"])

        if not storage_url:
            continue

        file_path = Path(storage_url)
        if not file_path.exists():
            # Try relative to the API directory
            resolved_path = api_dir / storage_url
            if resolved_path.exists():
                file_path = resolved_path

        if not file_path.exists():
            # Try relative to current working directory uploads
            resolved_path = Path("uploads") / Path(storage_url).name
            if resolved_path.exists():
                file_path = resolved_path

        if not file_path.exists():
            # Try upload_dir from settings
            from app.core.config import get_settings
            resolved_path = Path(get_settings().upload_dir) / Path(storage_url).name
            if resolved_path.exists():
                file_path = resolved_path

        if not file_path.exists():
            continue

        try:
            content = file_path.read_bytes()
            text = extract_text_from_bytes(content, filename)
            chunks = chunk_text(text)

            for chunk in chunks:
                chunk_vector = embedding_service.embed(chunk)
                # Compute cosine similarity (both are normalized)
                similarity = float(sum(q * c for q, c in zip(query_vector, chunk_vector)))
                if similarity >= min_score:
                    results.append({
                        "content": chunk,
                        "document_id": doc_id,
                        "source_type": "document",
                        "filename": filename,
                        "score": similarity,
                    })
        except Exception as e:
            # Do not crash the retrieval, just skip this document or log it
            print(f"Fallback retrieval failed for document {filename}: {e}")
            continue

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
