from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.auth import CurrentUser, assert_chat_owner, get_current_user
from app.core.config import get_settings
from app.db.session import get_pool
from app.schemas.chat import ChatStreamRequest
from app.services.embeddings import get_embedding_service
from app.services.llm_gateway import LLMGateway
from app.services.memory import retrieve_memory, store_message_embedding, vector_literal
from app.services.prompt_builder import build_citations, build_messages, wants_exhaustive_list
from app.services.redis_client import RedisService
from app.services.streaming import sse_event
from app.services.web_retrieval import WebRetrievalService

router = APIRouter(prefix="/chat", tags=["streaming"])


def usage_provider(settings) -> str:
    return "openrouter" if "openrouter.ai" in (settings.llm_base_url or "") else "openai"


def usage_model(settings) -> str:
    return settings.default_model or settings.cheap_model or "openai/gpt-4o-mini"


async def record_usage(pool, settings, workspace_id: str, chat_id: str, total_tokens: int) -> None:
    cost = (total_tokens / 1_000_000) * 0.15
    await pool.execute(
        """
        INSERT INTO usage_logs (
            workspace_id,
            chat_id,
            provider,
            model,
            total_tokens,
            estimated_cost_usd,
            status
        )
        VALUES ($1, $2, $3, $4, $5, $6, 'success')
        """,
        workspace_id,
        chat_id,
        usage_provider(settings),
        usage_model(settings),
        total_tokens,
        cost,
    )


def should_prompt_web(query: str, force_web: bool, skip_prompt: bool) -> bool:
    if force_web or skip_prompt:
        return False
    lowered = query.lower()
    return any(term in lowered for term in ["today", "latest", "current", "news", "price", "2026", "web"])

def needs_web(query: str, force_web: bool) -> bool:
    return force_web or wants_exhaustive_list(query)


async def retrieve_document_chunks(pool, embedding_service, workspace_id: str, query: str, document_ids: list[str]) -> list[dict]:
    """Retrieve relevant chunks from uploaded documents via pgvector similarity."""
    if not document_ids:
        return []
    query_vector = vector_literal(embedding_service.embed(query))
    rows = await pool.fetch(
        """
        SELECT
            me.content_chunk,
            me.document_id,
            me.source_type,
            d.filename,
            1 - (me.embedding <=> $1::vector) AS similarity
        FROM message_embeddings me
        LEFT JOIN documents d ON d.id = me.document_id
        WHERE me.workspace_id = $2
          AND me.source_type = 'document'
          AND me.document_id = ANY($3::uuid[])
        ORDER BY me.embedding <=> $1::vector
        LIMIT 10
        """,
        query_vector,
        workspace_id,
        document_ids,
    )
    res = [
        {
            "content": row["content_chunk"],
            "document_id": str(row["document_id"]) if row["document_id"] else None,
            "source_type": "document",
            "filename": row["filename"],
            "score": float(row["similarity"] or 0),
        }
        for row in rows
        if row["similarity"] is None or float(row["similarity"]) >= 0.40
    ]
    if not res:
        from app.services.document_fallback import retrieve_document_chunks_fallback
        res = await retrieve_document_chunks_fallback(
            pool, embedding_service, workspace_id, query, document_ids, limit=10, min_score=0.40
        )
    return res



@router.post("/stream")
async def stream_chat(payload: ChatStreamRequest, request: Request, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_chat_owner(pool, user.id, payload.workspace_id, payload.chat_id)
    settings = get_settings()
    embeddings = get_embedding_service()
    redis_service = RedisService(settings)
    await redis_service.enforce_limit(f"rate:user:{user.id}:chat", limit=60, window_seconds=3600)

    if should_prompt_web(payload.message, payload.force_web, payload.skip_web_prompt):
        async def prompt_generator():
            yield sse_event("action_required", {"action": "web_search"})
        return StreamingResponse(prompt_generator(), media_type="text/event-stream")

    if payload.advanced_search:
        # Delegate to LangGraph advanced search agent
        from app.agents.langgraph_agent import run_advanced_search

        history_rows = await pool.fetch(
            "SELECT role, content FROM messages WHERE workspace_id = $1 AND chat_id = $2 ORDER BY created_at ASC LIMIT 20",
            payload.workspace_id,
            payload.chat_id,
        )

        async def advanced_event_generator():
            yield sse_event("status", {"content": "Saving your message..."})
            user_row = await pool.fetchrow(
                "INSERT INTO messages (workspace_id, chat_id, role, content) VALUES ($1, $2, 'user', $3) RETURNING id",
                payload.workspace_id,
                payload.chat_id,
                payload.message,
            )
            await store_message_embedding(pool, embeddings, str(user_row["id"]), payload.workspace_id, payload.chat_id, payload.message)

            yield sse_event("status", {"content": "Starting advanced multi-step search..."})

            final_text = []
            async for event_type, data in run_advanced_search(
                query=payload.message,
                workspace_id=payload.workspace_id,
                chat_id=payload.chat_id,
                document_ids=payload.document_ids,
                history=[dict(row) for row in history_rows],
                force_web=payload.force_web,
                pool=pool,
                settings=settings,
                embedding_service=embeddings,
                redis_service=redis_service,
            ):
                if event_type == "answer_delta":
                    final_text.append(data)
                elif event_type == "usage":
                    await record_usage(pool, settings, payload.workspace_id, payload.chat_id, data)
                    continue
                yield sse_event(event_type, {"content": data} if isinstance(data, str) else data)

            assistant_content = "".join(final_text)
            if assistant_content:
                assistant_row = await pool.fetchrow(
                    "INSERT INTO messages (workspace_id, chat_id, role, content, reasoning_summary) VALUES ($1, $2, 'assistant', $3, $4) RETURNING id",
                    payload.workspace_id,
                    payload.chat_id,
                    assistant_content,
                    "Advanced search agent response.",
                )
                await store_message_embedding(pool, embeddings, str(assistant_row["id"]), payload.workspace_id, payload.chat_id, assistant_content)
                await pool.execute("UPDATE chat_sessions SET updated_at = now() WHERE id = $1", payload.chat_id)

        return StreamingResponse(advanced_event_generator(), media_type="text/event-stream")

    # Standard pipeline (with document context support)
    web = WebRetrievalService(settings, redis_service)
    llm = LLMGateway(settings)

    async def event_generator():
        yield sse_event("status", {"content": "Saving your message..."})
        user_row = await pool.fetchrow(
            "INSERT INTO messages (workspace_id, chat_id, role, content) VALUES ($1, $2, 'user', $3) RETURNING id",
            payload.workspace_id,
            payload.chat_id,
            payload.message,
        )
        await store_message_embedding(pool, embeddings, str(user_row["id"]), payload.workspace_id, payload.chat_id, payload.message)

        # Fetch history early for context and query optimization
        history_rows = await pool.fetch(
            "SELECT role, content FROM messages WHERE workspace_id = $1 AND chat_id = $2 ORDER BY created_at ASC LIMIT 20",
            payload.workspace_id,
            payload.chat_id,
        )
        history_list = [dict(row) for row in history_rows]

        yield sse_event("status", {"content": "Checking previous workspace conversations..."})
        search_query = payload.message
        if history_list:
            yield sse_event("status", {"content": "Optimizing search query..."})
            from app.agents.langgraph_agent import rewrite_query
            search_query = await rewrite_query(payload.message, history_list, settings)
            yield sse_event("reasoning_summary", {"content": f"Optimized query: \"{search_query}\""})

        exhaustive_list = wants_exhaustive_list(payload.message)
        memory_chunks = [] if exhaustive_list else await retrieve_memory(pool, embeddings, payload.workspace_id, search_query)
        yield sse_event("reasoning_summary", {"content": f"Found {len(memory_chunks)} relevant memory candidates."})

        # Retrieve document context
        document_chunks = []
        if payload.document_ids:
            yield sse_event("status", {"content": "Searching uploaded documents..."})
            document_chunks = await retrieve_document_chunks(pool, embeddings, payload.workspace_id, search_query, payload.document_ids)
            yield sse_event("reasoning_summary", {"content": f"Found {len(document_chunks)} relevant document chunks."})

        web_sources = []
        if needs_web(payload.message, payload.force_web):
            yield sse_event("status", {"content": "Fetching live web sources..."})
            web_sources = await web.advanced_search(search_query) if exhaustive_list else await web.retrieve(search_query)
            yield sse_event("reasoning_summary", {"content": f"Collected {len(web_sources)} live web sources."})

        prompt = build_messages(payload.message, history_list, memory_chunks, web_sources, document_chunks)
        citations = build_citations(memory_chunks, web_sources, document_chunks)
        yield sse_event("citations", [citation.model_dump() for citation in citations])
        yield sse_event("status", {"content": "Generating final answer..."})

        final_text = []
        async for token in llm.stream_answer(prompt):
            if isinstance(token, str):
                final_text.append(token)
                yield sse_event("answer_delta", {"content": token})
            elif isinstance(token, dict) and "usage" in token:
                await record_usage(pool, settings, payload.workspace_id, payload.chat_id, token["usage"])

        assistant_content = "".join(final_text)
        assistant_row = await pool.fetchrow(
            """
            INSERT INTO messages (workspace_id, chat_id, role, content, reasoning_summary)
            VALUES ($1, $2, 'assistant', $3, $4)
            RETURNING id
            """,
            payload.workspace_id,
            payload.chat_id,
            assistant_content,
            f"Used {len(memory_chunks)} memory chunks, {len(document_chunks)} document chunks, and {len(web_sources)} web sources.",
        )
        await store_message_embedding(pool, embeddings, str(assistant_row["id"]), payload.workspace_id, payload.chat_id, assistant_content)
        await pool.execute("UPDATE chat_sessions SET updated_at = now() WHERE id = $1", payload.chat_id)
        yield sse_event("done", {"ok": True})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
