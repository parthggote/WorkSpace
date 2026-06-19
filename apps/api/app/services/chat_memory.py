from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.services.embeddings import EmbeddingService
from app.services.memory import vector_literal
from app.services.reranker import lexical_overlap, recency_score


RECENCY_REFERENCE_TERMS = {
    "last conversation",
    "previous conversation",
    "previous chat",
    "last chat",
    "what were we discussing",
    "what did we discuss",
}


def mentions_recent_chat(query: str) -> bool:
    lowered = query.lower()
    return any(term in lowered for term in RECENCY_REFERENCE_TERMS)


def extract_chat_title_hint(query: str) -> str | None:
    match = re.search(r"\bchat[\d_-]*\b", query.lower())
    return match.group(0) if match else None


def build_chat_memory_summary(messages: list[dict[str, Any]], *, max_chars: int = 1800) -> str:
    if not messages:
        return ""

    lines: list[str] = []
    for message in messages[-12:]:
        role = message.get("role")
        content = " ".join(str(message.get("content") or "").split())
        if role not in {"user", "assistant"} or not content:
            continue
        lines.append(f"{role}: {content}")

    summary = "\n".join(lines)
    if len(summary) <= max_chars:
        return summary
    return summary[-max_chars:].lstrip()


async def refresh_chat_memory_summary(
    pool,
    embedding_service: EmbeddingService,
    workspace_id: str,
    chat_id: str,
) -> str:
    rows = await pool.fetch(
        """
        SELECT role, content
        FROM messages
        WHERE workspace_id = $1
          AND chat_id = $2
        ORDER BY created_at ASC
        """,
        workspace_id,
        chat_id,
    )
    summary = build_chat_memory_summary([dict(row) for row in rows])
    if not summary:
        return ""

    vector = vector_literal(embedding_service.embed(summary))
    await pool.execute(
        """
        UPDATE chat_sessions
        SET summary = $3,
            last_summarized_at = now(),
            updated_at = now()
        WHERE workspace_id = $1
          AND id = $2
        """,
        workspace_id,
        chat_id,
        summary,
    )
    await pool.execute(
        """
        DELETE FROM message_embeddings
        WHERE workspace_id = $1
          AND chat_id = $2
          AND source_type = 'summary'
        """,
        workspace_id,
        chat_id,
    )
    await pool.execute(
        """
        INSERT INTO message_embeddings (
            message_id,
            workspace_id,
            chat_id,
            source_type,
            content_chunk,
            embedding
        )
        VALUES (NULL, $1, $2, 'summary', $3, $4::vector)
        """,
        workspace_id,
        chat_id,
        summary,
        vector,
    )
    return summary


async def retrieve_workspace_chat_context(
    pool,
    embedding_service: EmbeddingService,
    workspace_id: str,
    current_chat_id: str,
    query: str,
    *,
    top_chats: int = 2,
    messages_per_chat: int = 8,
) -> list[dict]:
    query_vector = vector_literal(embedding_service.embed(query))
    chats = await pool.fetch(
        """
        SELECT
            cs.id,
            cs.title,
            cs.summary,
            cs.updated_at,
            1 - (me.embedding <=> $1::vector) AS similarity
        FROM chat_sessions cs
        LEFT JOIN message_embeddings me
          ON me.workspace_id = cs.workspace_id
         AND me.chat_id = cs.id
         AND me.source_type = 'summary'
        WHERE cs.workspace_id = $2
          AND cs.id <> $3
        ORDER BY cs.updated_at DESC
        LIMIT 50
        """,
        query_vector,
        workspace_id,
        current_chat_id,
    )
    if not chats:
        return []

    message_hits = await pool.fetch(
        """
        SELECT
            me.chat_id,
            max(1 - (me.embedding <=> $1::vector)) AS similarity
        FROM message_embeddings me
        WHERE me.workspace_id = $2
          AND me.source_type = 'chat'
          AND me.chat_id IS NOT NULL
          AND me.chat_id IS DISTINCT FROM $3::uuid
        GROUP BY me.chat_id
        ORDER BY similarity DESC
        LIMIT 50
        """,
        query_vector,
        workspace_id,
        current_chat_id,
    )
    message_similarity_by_chat = {
        str(row["chat_id"]): float(row["similarity"] or 0) for row in message_hits
    }

    title_hint = extract_chat_title_hint(query)
    recency_reference = mentions_recent_chat(query)
    scored = []
    for index, chat in enumerate(chats):
        title = chat["title"] or ""
        summary = chat["summary"] or ""
        updated_at = chat["updated_at"]
        if isinstance(updated_at, datetime) and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        similarity = max(
            float(chat["similarity"] or 0),
            message_similarity_by_chat.get(str(chat["id"]), 0.0),
        )
        title_score = 1.0 if title_hint and title_hint == title.lower() else lexical_overlap(query, title)
        summary_score = lexical_overlap(query, summary)
        recent_score = recency_score(updated_at, half_life_days=14)
        explicit_title_boost = 1.5 if title_hint and title_hint == title.lower() else 0.0
        recency_boost = max(0.0, 1.5 - (index * 0.25)) if recency_reference else 0.0
        score = (
            0.45 * similarity
            + 0.20 * title_score
            + 0.15 * summary_score
            + 0.20 * recent_score
            + explicit_title_boost
            + recency_boost
        )
        scored.append((score, chat))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected_chats = [chat for _, chat in scored[:top_chats]]

    chunks: list[dict] = []
    for chat in selected_chats:
        rows = await pool.fetch(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE workspace_id = $1
              AND chat_id = $2
              AND role IN ('user', 'assistant')
            ORDER BY created_at DESC
            LIMIT $3
            """,
            workspace_id,
            chat["id"],
            messages_per_chat,
        )
        ordered_rows = list(reversed(rows))
        transcript = "\n".join(
            f"{row['role']}: {row['content']}" for row in ordered_rows if row["content"]
        )
        if not transcript and chat["summary"]:
            transcript = chat["summary"]
        if not transcript:
            continue
        chunks.append(
            {
                "content": transcript,
                "chat_id": str(chat["id"]),
                "message_id": str(ordered_rows[-1]["id"]) if ordered_rows else None,
                "source_type": "chat",
                "chat_title": chat["title"] or "Previous chat",
                "score": 1.0,
                "retrieval_reason": "chat_summary_context",
            }
        )
    return chunks
