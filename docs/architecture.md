# Architecture

The application is a monorepo with a Next.js frontend, FastAPI backend, Supabase Auth, Supabase PostgreSQL with pgvector, Redis, Tavily Search, LangGraph orchestration, and OpenRouter-compatible LLM calls.

## Request Flow

```text
User -> Next.js -> FastAPI /chat/stream -> LangGraph
     -> workspace memory retrieval
     -> optional Tavily web retrieval
     -> reranking
     -> context compression
     -> prompt builder
     -> OpenRouter streaming
     -> citations and persistence
```

The backend starts the SSE response before retrieval finishes so the UI can show safe status updates such as "Checking workspace memory" and "Searching live web".

## Core Boundaries

- The frontend owns workspace and chat interaction surfaces.
- The backend owns auth verification, workspace ownership checks, retrieval, streaming, provider calls, usage logging, and background jobs.
- PostgreSQL owns durable state and vector search.
- Redis owns ephemeral state: rate limits, cache, Celery broker/result channels, stream status, and short-lived counters.
- Background workers own embeddings, summaries, document chunking, document embeddings, usage aggregation, and cache cleanup.

## Workspace Isolation

Every durable entity that can leak user data carries `workspace_id` directly, including messages, embeddings, documents, document chunks, retrieval runs, web sources, tool calls, usage logs, and jobs. Queries must filter by `workspace_id` before vector search, reranking, or citation construction.

The schema also uses composite foreign keys such as `(chat_id, workspace_id)` to prevent a message from referencing a chat in a different workspace.

## Agent Design

LangGraph should run controlled branches:

```text
intent router -> selected retrieval tools -> reranker -> compressor -> one final LLM call
```

Avoid recursive tool loops for the MVP because they increase cost, latency, and failure modes.

## Retrieval Sources

- Chat messages and chat summaries use `source_type='message'` or `source_type='summary'`.
- Uploaded documents use `source_type='document'`.
- Live web sources are stored separately in `web_sources` and can be attached to messages for citations.

All retrieval candidates are normalized into a common reranking shape before context compression.
