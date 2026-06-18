# Deployment

Recommended deployment:

- Frontend: Vercel
- Backend: Render
- Background Worker: Render Celery worker
- Database and Auth: Supabase
- Redis: Upstash Redis
- Search: Tavily Search API
- LLM Gateway: OpenRouter
- Embeddings: OpenAI-compatible remote embeddings through OpenAI or OpenRouter

## Environment Separation

Use separate values for local, preview, and production.

Frontend public variables:

```env
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Backend secrets:

```env
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
TAVILY_API_KEY=
TAVILY_SEARCH_DEPTH=basic
LLM_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openai/gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=768
EMBEDDING_BATCH_SIZE=24
RERANKER_MODEL=BAAI/bge-reranker-base
```

Only `NEXT_PUBLIC_*` variables may be exposed to the browser.

For OpenRouter embeddings, use the same OpenRouter key if desired:

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_openrouter_key
EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIMENSIONS=768
```

`EMBEDDING_PROVIDER=openai` means the backend uses an OpenAI-compatible embeddings client; it does not require the provider to be direct OpenAI.

## Migration Order

1. Create Supabase project.
2. Enable Auth providers.
3. Apply migrations from `supabase/migrations`.
4. Provision Upstash Redis.
5. Configure backend environment variables.
6. Deploy backend and confirm health checks.
7. Configure frontend environment variables.
8. Deploy frontend.
9. Run a smoke test: sign in, create workspace, create chat, stream answer, confirm message persistence.

## Redis and Celery-Style Workers

For production deployment, run a worker process that consumes Redis-backed Celery queues:

- `embeddings`
- `summaries`
- `documents`
- `maintenance`

The database `background_jobs` table provides durable audit status even when Redis is the broker.

Render worker command should keep memory bounded:

```bash
python -m celery -A app.jobs.celery_app worker --loglevel=info --pool=solo --concurrency=1 --prefetch-multiplier=1 --max-tasks-per-child=10
```

## Secret Hygiene

Do not paste real secrets into README, issue comments, screenshots, logs, or committed files. Rotate any key that is accidentally exposed.

## Health Checks

Backend health should verify:

- database connection;
- Redis connection;
- migration version availability;
- model provider configuration presence without echoing secrets.

## Rollback

Keep migrations backward-compatible during preview. If a deployment fails, roll back the backend first, then frontend. Avoid destructive migrations until exported data has been backed up.
