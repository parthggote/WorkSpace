from app.services.embeddings import EmbeddingService
from app.services.memory import vector_literal


DOCUMENT_FOCUSED_TERMS = {
    "attached",
    "attachment",
    "document",
    "file",
    "pdf",
    "docx",
    "uploaded",
    "this doc",
    "this document",
}

DOCUMENT_SUMMARY_TERMS = {
    "summary",
    "summarize",
    "summarise",
    "overview",
    "brief",
    "key points",
    "main points",
    "tl;dr",
}


def is_document_focused_query(query: str, document_ids: list[str] | None) -> bool:
    if not document_ids:
        return False
    lowered = query.lower()
    return any(term in lowered for term in DOCUMENT_FOCUSED_TERMS)


def is_document_summary_query(query: str, document_ids: list[str] | None) -> bool:
    if not document_ids:
        return False
    lowered = query.lower()
    return any(term in lowered for term in DOCUMENT_SUMMARY_TERMS) and (
        is_document_focused_query(query, document_ids) or len(document_ids) == 1
    )


async def retrieve_ordered_document_chunks(
    pool,
    workspace_id: str,
    document_ids: list[str],
    limit: int = 12,
) -> list[dict]:
    if not document_ids:
        return []

    rows = await pool.fetch(
        """
        SELECT
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.filename
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.workspace_id = $1
          AND dc.document_id = ANY($2::uuid[])
          AND d.status = 'ready'
        ORDER BY d.created_at DESC, dc.document_id, dc.chunk_index
        LIMIT $3
        """,
        workspace_id,
        document_ids,
        limit,
    )
    return [
        {
            "content": row["content"],
            "document_id": str(row["document_id"]),
            "source_type": "document",
            "filename": row["filename"],
            "chunk_index": row["chunk_index"],
            "score": 1.0,
            "retrieval_reason": "ordered_document_context",
        }
        for row in rows
    ]


async def retrieve_document_chunks(
    pool,
    embedding_service: EmbeddingService,
    workspace_id: str,
    query: str,
    document_ids: list[str],
    *,
    limit: int = 10,
    min_score: float = 0.40,
    force_ordered_context: bool = False,
) -> list[dict]:
    """Retrieve chunks from selected uploaded documents.

    Summary-style requests are intentionally not gated only by vector similarity:
    "summarize this document" is semantically relevant to the whole file, even if
    no individual chunk strongly matches the generic query text.
    """
    if not document_ids:
        return []

    if force_ordered_context:
        return await retrieve_ordered_document_chunks(pool, workspace_id, document_ids, limit=limit)

    query_vector = vector_literal(embedding_service.embed(query))
    rows = await pool.fetch(
        """
        SELECT
            me.content_chunk,
            me.document_id,
            me.source_type,
            me.chunk_index,
            d.filename,
            1 - (me.embedding <=> $1::vector) AS similarity
        FROM message_embeddings me
        JOIN documents d ON d.id = me.document_id
        WHERE me.workspace_id = $2
          AND me.source_type = 'document'
          AND me.document_id = ANY($3::uuid[])
          AND d.status = 'ready'
        ORDER BY me.embedding <=> $1::vector
        LIMIT $4
        """,
        query_vector,
        workspace_id,
        document_ids,
        max(limit * 2, limit),
    )
    chunks = [
        {
            "content": row["content_chunk"],
            "document_id": str(row["document_id"]) if row["document_id"] else None,
            "source_type": "document",
            "filename": row["filename"],
            "chunk_index": row["chunk_index"],
            "score": float(row["similarity"] or 0),
            "retrieval_reason": "vector_document_context",
        }
        for row in rows
        if row["similarity"] is None or float(row["similarity"]) >= min_score
    ][:limit]

    if chunks:
        return chunks

    ordered_chunks = await retrieve_ordered_document_chunks(pool, workspace_id, document_ids, limit=limit)
    if ordered_chunks:
        return ordered_chunks

    from app.services.document_fallback import retrieve_document_chunks_fallback

    return await retrieve_document_chunks_fallback(
        pool,
        embedding_service,
        workspace_id,
        query,
        document_ids,
        limit=limit,
        min_score=min_score,
    )
