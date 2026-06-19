"""LangGraph-based multi-step advanced search agent."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from app.core.config import Settings
from app.services.embeddings import EmbeddingService
from app.services.llm_gateway import LLMGateway
from app.services.memory import retrieve_memory, vector_literal
from app.services.prompt_builder import build_citations, build_messages
from app.services.reranker import AdvancedReranker, RetrievalCandidate
from app.services.redis_client import RedisService
from app.services.web_retrieval import WebRetrievalService


WEB_TRIGGER_TERMS = ["today", "latest", "current", "news", "price", "2026", "web", "search", "find online"]


class AgentState(TypedDict, total=False):
    query: str
    search_query: str
    workspace_id: str
    chat_id: str
    document_ids: list[str]
    history: list[dict]
    force_web: bool
    # Retrieval results
    memory_chunks: list[dict]
    web_sources: list[dict]
    document_chunks: list[dict]
    # Routing flags
    needs_web: bool
    has_documents: bool
    # Output
    status_messages: list[str]
    merged_candidates: list[dict]


async def rewrite_query(query: str, history: list[dict], settings: Settings) -> str:
    if not history:
        return query

    # Format recent history for the LLM
    formatted_history = []
    for msg in history[-5:]: # last 5 messages
        role = msg.get("role")
        content = msg.get("content")
        if role in ("user", "assistant") and content:
            formatted_history.append(f"{role.capitalize()}: {content}")

    if not formatted_history:
        return query

    history_str = "\n".join(formatted_history)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a search query optimizer. Your job is to convert a conversational follow-up message "
                "and its history into a single, concise standalone search query consisting of search keywords. "
                "Never output conversational instructions, meta-commands (like 'search again', 'find on internet', 'google it'), "
                "or questions. Extract the actual search terms, subjects, and topics being referred to in the conversation history.\n\n"
                "Example 1:\n"
                "History:\n"
                "User: What is the score of yesterday's game?\n"
                "Assistant: It ended 2-2.\n"
                "New Message: check on the internet again\n"
                "Optimized Search Query: yesterday game score results\n\n"
                "Example 2:\n"
                "History:\n"
                "User: Tell me about SofaScore squad ratings for Portugal vs DR Congo.\n"
                "Assistant: I don't have those ratings in my database.\n"
                "New Message: please search for them\n"
                "Optimized Search Query: Portugal vs DR Congo SofaScore squad ratings\n\n"
                "Example 3:\n"
                "History:\n"
                "User: What is the stock price of Apple?\n"
                "Assistant: Apple stock is currently $180.\n"
                "New Message: latest news on this\n"
                "Optimized Search Query: Apple stock latest news\n\n"
                "Now generate the optimized search query for the following conversation:"
            )
        },
        {
            "role": "user",
            "content": f"Conversation History:\n{history_str}\n\nNew User Message: {query}\n\nOptimized Search Query:"
        }
    ]

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.llm_api_key or "missing", base_url=settings.llm_base_url)
        response = await client.chat.completions.create(
            model=settings.cheap_model or settings.default_model,
            messages=prompt,
            max_tokens=60,
            temperature=0.0,
        )
        rewritten = response.choices[0].message.content.strip().strip('"').strip("'")
        if rewritten:
            return rewritten
    except Exception as e:
        print(f"Failed to rewrite query: {e}")
    return query


def classify_intent(state: AgentState) -> dict:
    """Determine which retrieval paths to activate."""
    query_lower = state["query"].lower()
    needs_web = state.get("force_web", False) or any(
        term in query_lower for term in WEB_TRIGGER_TERMS
    )
    has_documents = bool(state.get("document_ids"))
    return {
        "needs_web": needs_web,
        "has_documents": has_documents,
        "status_messages": [
            f"Intent classified: web={'yes' if needs_web else 'no'}, "
            f"docs={'yes' if has_documents else 'no'}"
        ],
    }


async def node_retrieve_memory(
    state: AgentState, pool, embedding_service: EmbeddingService
) -> dict:
    """Retrieve relevant memory chunks from workspace conversations."""
    query = state.get("search_query") or state["query"]
    chunks = await retrieve_memory(
        pool, embedding_service, state["workspace_id"], query
    )
    return {
        "memory_chunks": chunks,
        "status_messages": [
            f"Retrieved {len(chunks)} memory chunks.",
            summarize_sources("workspace memory", chunks, "chat_title"),
        ],
    }


async def node_retrieve_documents(
    state: AgentState, pool, embedding_service: EmbeddingService
) -> dict:
    """Retrieve relevant document chunks from uploaded documents."""
    document_ids = state.get("document_ids", [])
    if not document_ids:
        return {"document_chunks": [], "status_messages": ["No documents to search."]}

    query = state.get("search_query") or state["query"]
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
        LIMIT 20
        """,
        query_vector,
        state["workspace_id"],
        document_ids,
    )
    chunks = [
        {
            "content": row["content_chunk"],
            "document_id": str(row["document_id"]) if row["document_id"] else None,
            "source_type": "document",
            "filename": row["filename"],
            "score": float(row["similarity"] or 0),
        }
        for row in rows
        if row["similarity"] is None or float(row["similarity"]) >= 0.45
    ]
    if not chunks:
        from app.services.document_fallback import retrieve_document_chunks_fallback
        chunks = await retrieve_document_chunks_fallback(
            pool,
            embedding_service,
            state["workspace_id"],
            query,
            document_ids,
            limit=20,
            min_score=0.45
        )
    return {
        "document_chunks": chunks,
        "status_messages": [
            f"Retrieved {len(chunks)} document chunks.",
            summarize_sources("document context", chunks, "filename"),
        ],
    }

import re
import asyncio
from urllib.parse import urlparse

URL_REGEX = re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)')


def source_host(url: str | None) -> str:
    if not url:
        return "source"
    host = urlparse(url).netloc.replace("www.", "")
    return host or "source"


def format_score(value) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "n/a"


def summarize_sources(label: str, items: list[dict], title_key: str, score_key: str = "score", limit: int = 5) -> str:
    if not items:
        return f"No {label} cleared the relevance threshold."
    lines = []
    for index, item in enumerate(items[:limit], start=1):
        title = item.get(title_key) or item.get("title") or item.get("filename") or source_host(item.get("url"))
        host = f" ({source_host(item.get('url'))})" if item.get("url") else ""
        score = format_score(item.get(score_key))
        lines.append(f"{index}. {title}{host}, score {score}")
    return f"Selected {label}:\n" + "\n".join(lines)

async def node_search_web(
    state: AgentState, settings: Settings, redis_service: RedisService | None
) -> dict:
    """Search the web via Tavily and extract direct URLs."""
    web_service = WebRetrievalService(settings, redis_service)
    
    # Use the original query to find URLs, as rewrite_query might have stripped them
    original_query = state["query"]
    search_query = state.get("search_query") or original_query
    
    urls = list(set(URL_REGEX.findall(original_query)))
    
    tasks = [web_service.advanced_search(search_query)]
    for url in urls:
        tasks.append(web_service.fetch_extract(url))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    sources = []
    # Process advanced search results
    if not isinstance(results[0], Exception):
        sources.extend(results[0])
        
    # Process direct URL extractions
    for i, url in enumerate(urls, start=1):
        res = results[i]
        if not isinstance(res, Exception) and res:
            sources.append({
                "title": f"Extracted Content from {url}",
                "url": url,
                "description": "Direct URL extraction",
                "content": res,
                "score": 0.99, # High score for direct user-provided links
                "source": "url_extract",
            })

    return {
        "web_sources": sources,
        "status_messages": [
            f"Collected {len(sources)} web sources (including {len(urls)} direct links).",
            summarize_sources("web sources", sources, "title"),
        ],
    }

def node_rerank_merge(state: AgentState) -> dict:
    """Merge and rerank all retrieval candidates."""
    candidates: list[RetrievalCandidate] = []

    for idx, chunk in enumerate(state.get("memory_chunks", [])):
        candidates.append(
            RetrievalCandidate(
                id=chunk.get("message_id") or f"memory:{idx}",
                text=chunk.get("content", ""),
                source_type="message",
                similarity=float(chunk.get("score", 0)),
                title=chunk.get("chat_title"),
                metadata=chunk,
            )
        )

    for idx, chunk in enumerate(state.get("document_chunks", [])):
        candidates.append(
            RetrievalCandidate(
                id=chunk.get("document_id") or f"doc:{idx}",
                text=chunk.get("content", ""),
                source_type="document",
                similarity=float(chunk.get("score", 0)),
                title=chunk.get("filename"),
                metadata=chunk,
            )
        )

    for idx, src in enumerate(state.get("web_sources", [])):
        candidates.append(
            RetrievalCandidate(
                id=src.get("url") or f"web:{idx}",
                text=src.get("content", ""),
                source_type="web",
                similarity=float(src.get("score", 0)),
                title=src.get("title"),
                metadata=src,
            )
        )

    ranker = AdvancedReranker(minimum_score=0.15)
    ranked = ranker.rerank(state["query"], candidates, top_k=8)

    merged = []
    for c in ranked:
        item = dict(c.metadata)
        item["rerank_score"] = c.rerank_score
        item["source_type"] = c.source_type
        merged.append(item)

    return {
        "merged_candidates": merged,
        "status_messages": [
            f"Reranked {len(candidates)} candidates into top {len(merged)} evidence candidates.",
            summarize_sources("reranked evidence", merged, "title", "rerank_score"),
        ],
    }


async def run_advanced_search(
    *,
    query: str,
    workspace_id: str,
    chat_id: str,
    document_ids: list[str],
    history: list[dict],
    force_web: bool,
    pool,
    settings: Settings,
    embedding_service: EmbeddingService,
    redis_service: RedisService | None,
) -> AsyncIterator[tuple[str, Any]]:
    """Run the advanced multi-step search pipeline and yield SSE-compatible events."""

    state: AgentState = {
        "query": query,
        "workspace_id": workspace_id,
        "chat_id": chat_id,
        "document_ids": document_ids,
        "history": history,
        "force_web": force_web,
        "memory_chunks": [],
        "web_sources": [],
        "document_chunks": [],
        "needs_web": False,
        "has_documents": False,
        "status_messages": [],
        "merged_candidates": [],
    }

    # Step 1: Classify intent
    yield ("status", "Classifying query intent...")
    intent_result = classify_intent(state)
    state.update(intent_result)
    for msg in intent_result.get("status_messages", []):
        yield ("reasoning_summary", msg)

    # Rewrite query based on context if history exists
    search_query = query
    if history:
        yield ("status", "Optimizing search query based on chat context...")
        search_query = await rewrite_query(query, history, settings)
        state["search_query"] = search_query
        yield ("reasoning_summary", f"Optimized query: \"{search_query}\"")

    # Step 2: Parallel retrieval
    yield ("status", "Running parallel retrieval...")
    retrieval_tasks = []
    retrieval_tasks.append(
        node_retrieve_memory(state, pool, embedding_service)
    )
    if state["has_documents"]:
        retrieval_tasks.append(
            node_retrieve_documents(state, pool, embedding_service)
        )
    if state["needs_web"]:
        retrieval_tasks.append(
            node_search_web(state, settings, redis_service)
        )

    results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            yield ("reasoning_summary", f"Retrieval error: {result}")
            continue
        if isinstance(result, dict):
            for key in ("memory_chunks", "web_sources", "document_chunks"):
                if key in result:
                    state[key] = result[key]
            for msg in result.get("status_messages", []):
                yield ("reasoning_summary", msg)

    # Step 3: Rerank and merge
    yield ("status", "Reranking and merging results...")
    merge_result = node_rerank_merge(state)
    state.update(merge_result)
    for msg in merge_result.get("status_messages", []):
        yield ("reasoning_summary", msg)

    # Step 4: Build context and citations
    merged = state.get("merged_candidates", [])
    memory_for_prompt = [m for m in merged if m.get("source_type") == "message"]
    doc_for_prompt = [m for m in merged if m.get("source_type") == "document"]
    web_for_prompt = [m for m in merged if m.get("source_type") == "web"]
    evidence_parts = []
    if memory_for_prompt:
        evidence_parts.append(f"{len(memory_for_prompt)} memory")
    if doc_for_prompt:
        evidence_parts.append(f"{len(doc_for_prompt)} document")
    if web_for_prompt:
        evidence_parts.append(f"{len(web_for_prompt)} web")
    yield (
        "reasoning_summary",
        "Answer context mix: " + ", ".join(evidence_parts) if evidence_parts else "Answer context mix: current chat only.",
    )

    prompt = build_messages(
        state["query"],
        state.get("history", []),
        memory_for_prompt,
        web_for_prompt,
        doc_for_prompt,
    )
    citations = build_citations(memory_for_prompt, web_for_prompt, doc_for_prompt)
    yield ("citations", [c.model_dump() for c in citations])

    # Step 5: Generate answer
    yield ("status", "Generating answer with advanced context...")
    llm = LLMGateway(settings)
    async for token in llm.stream_answer(prompt):
        if isinstance(token, str):
            yield ("answer_delta", token)
        elif isinstance(token, dict) and "usage" in token:
            yield ("usage", token["usage"])

    yield ("done", {"ok": True})
