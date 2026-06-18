# Multi-Workspace AI Chat

Multi-workspace AI chat application architecture for the June 2026 AI intern screening assignment. The product is designed around isolated workspaces, persistent chat history, streaming status updates, cross-chat semantic retrieval, live web retrieval without built-in browsing plugins, and strict API cost controls.

## Core Features

- Supabase Auth with backend ownership checks for every workspace, chat, message, document, and retrieval query.
- Server-Sent Events chat streaming with safe status and reasoning-summary events before final answer deltas.
- PostgreSQL plus pgvector memory retrieval using 768-dimensional remote embeddings.
- Redis-backed caching, rate limits, cost counters, stream state, and Celery-compatible job brokering.
- Tavily-powered web retrieval with backend ranking, reranking, compression, and citations.
- Document upload architecture that uses Supabase Storage, Celery workers, remote batched embeddings, and the same retrieval/citation pipeline as chat memory.
- Usage logs, tool calls, background job records, and retrieval run metadata for observability and cost tracking.

## Repository Shape

```text
apps/api/                 FastAPI backend application
docs/                     Architecture, deployment, retrieval, streaming, security docs
supabase/migrations/      PostgreSQL and pgvector schema migrations
docker-compose.yml        Local PostgreSQL + Redis dependencies
.env.example              Placeholder-only environment variable template
```

## Local Dependencies

Use Docker Compose for local infrastructure:

```bash
docker compose up -d postgres redis
```

The local Postgres service enables `pgvector` through the Supabase migration. Redis is used for cache, rate limits, and the Celery-style broker/result backend.

## Environment

Copy `.env.example` to your local `.env` and fill values outside source control. Never commit real secrets.

Key backend variables:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `TAVILY_API_KEY`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `DEFAULT_MODEL`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSIONS`
- `EMBEDDING_BATCH_SIZE`
- `RERANKER_MODEL`

Key frontend variables:

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Database Setup

Apply migrations in `supabase/migrations` to a Supabase Postgres project with pgvector support.

The initial schema includes:

- Workspace-scoped `workspaces`, `chat_sessions`, `messages`, `documents`, and `document_chunks`.
- `message_embeddings` with `vector(768)` and workspace-filtered HNSW indexes.
- Retrieval observability through `retrieval_runs` and `retrieval_results`.
- Web citations through `web_sources`.
- Celery-style durable background tracking through `background_jobs`.
- RLS policies that require `auth.uid()` ownership through the workspace owner.

## Documentation

- [Architecture](docs/architecture.md)
- [Streaming](docs/streaming.md)
- [Cross-Chat Retrieval](docs/cross-chat-retrieval.md)
- [Web Retrieval](docs/web-retrieval.md)
- [API Cost Strategy](docs/api-cost-strategy.md)
- [Authentication](docs/authentication.md)
- [Security](docs/security.md)
- [Deployment](docs/deployment.md)
- [Implementation Audit](docs/implementation-audit.md)

## Deployment Targets

- Frontend: Vercel
- Backend: Render
- Background worker: Render Celery worker
- Database/Auth: Supabase
- Redis: Upstash Redis
- Search: Tavily
- LLM Gateway: OpenRouter
- Embeddings: OpenAI-compatible remote embeddings through OpenAI or OpenRouter

See [docs/deployment.md](docs/deployment.md) for environment separation, migration order, and secret hygiene rules.
