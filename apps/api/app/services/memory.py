from app.services.embeddings import EmbeddingService
from app.services.reranker import AdvancedReranker, RetrievalCandidate


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


async def store_message_embedding(pool, embedding_service: EmbeddingService, message_id: str, workspace_id: str, chat_id: str, content: str) -> None:
    vector = vector_literal(embedding_service.embed(content))
    await pool.execute(
        """
        INSERT INTO message_embeddings (message_id, workspace_id, chat_id, source_type, content_chunk, embedding)
        VALUES ($1, $2, $3, 'chat', $4, $5::vector)
        """,
        message_id,
        workspace_id,
        chat_id,
        content,
        vector,
    )


async def retrieve_memory(pool, embedding_service: EmbeddingService, workspace_id: str, query: str, limit: int = 5) -> list[dict]:
    vector = vector_literal(embedding_service.embed(query))
    rows = await pool.fetch(
        """
        SELECT
            me.content_chunk,
            me.chat_id,
            me.message_id,
            me.source_type,
            cs.title AS chat_title,
            m.created_at,
            1 - (me.embedding <=> $1::vector) AS similarity
        FROM message_embeddings me
        LEFT JOIN messages m ON m.id = me.message_id
        LEFT JOIN chat_sessions cs ON cs.id = me.chat_id
        WHERE me.workspace_id = $2
        ORDER BY me.embedding <=> $1::vector
        LIMIT 30
        """,
        vector,
        workspace_id,
    )
    candidates = [
        {
            "content": row["content_chunk"],
            "chat_id": str(row["chat_id"]) if row["chat_id"] else None,
            "message_id": str(row["message_id"]) if row["message_id"] else None,
            "source_type": row["source_type"],
            "chat_title": row["chat_title"],
            "score": float(row["similarity"] or 0),
        }
        for row in rows
        if row["similarity"] is None or float(row["similarity"]) >= 0.55
    ]
    typed = [
        RetrievalCandidate(
            id=item.get("message_id") or f"{item.get('source_type')}:{index}",
            text=item["content"],
            source_type="message" if item["source_type"] == "chat" else item["source_type"],
            similarity=float(item["score"]),
            title=item.get("chat_title"),
            metadata=item,
        )
        for index, item in enumerate(candidates)
    ]
    ranked = AdvancedReranker(minimum_score=0.25).rerank(query, typed, top_k=limit)
    output = []
    for candidate in ranked:
        item = dict(candidate.metadata)
        item["rerank_score"] = candidate.rerank_score
        output.append(item)
    return output


async def retrieve_document_context(
    pool,
    embedding_service: EmbeddingService,
    workspace_id: str,
    query: str,
    document_ids: list[str],
    limit: int = 5,
) -> list[dict]:
    if not document_ids:
        return []

    vector = vector_literal(embedding_service.embed(query))
    rows = await pool.fetch(
        """
        SELECT
            me.content_chunk,
            me.document_id,
            me.document_chunk_id,
            me.chunk_index,
            d.filename,
            d.created_at,
            1 - (me.embedding <=> $1::vector) AS similarity
        FROM message_embeddings me
        JOIN documents d ON d.id = me.document_id
        WHERE me.workspace_id = $2
          AND me.source_type = 'document'
          AND me.document_id = ANY($3::uuid[])
        ORDER BY me.embedding <=> $1::vector
        LIMIT 30
        """,
        vector,
        workspace_id,
        document_ids,
    )
    candidates = [
        RetrievalCandidate(
            id=str(row["document_chunk_id"] or row["document_id"]),
            text=row["content_chunk"],
            source_type="document",
            similarity=float(row["similarity"] or 0),
            created_at=row["created_at"],
            title=row["filename"],
            metadata={
                "content": row["content_chunk"],
                "document_id": str(row["document_id"]),
                "document_chunk_id": str(row["document_chunk_id"]) if row["document_chunk_id"] else None,
                "chunk_index": row["chunk_index"],
                "filename": row["filename"],
                "score": float(row["similarity"] or 0),
            },
        )
        for row in rows
        if row["similarity"] is None or float(row["similarity"]) >= 0.45
    ]
    ranked = AdvancedReranker(minimum_score=0.20).rerank(query, candidates, top_k=limit)
    output = []
    for candidate in ranked:
        item = dict(candidate.metadata)
        item["rerank_score"] = candidate.rerank_score
        output.append(item)
    return output
