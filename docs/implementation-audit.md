# Implementation Audit

This document tracks places where the current implementation is intentionally incomplete, uses local-development fallbacks, or still needs production wiring. It exists so the project does not accidentally present scaffold behavior as finished product behavior.

## Fixed in Current Pass

- Frontend UI now uses Shadcn-style component primitives under `apps/web/src/components/ui`.
- Custom raw card/button/textarea/scroll panel markup was replaced across the main workspace UI.
- The fake local streaming answer fallback was removed. If the backend stream fails, the UI now reports the failure instead of inventing an answer.
- Remote Google font dependency was removed so builds do not rely on network font fetching.

## Still Needs Production Work

### Frontend data loading

The workspace, chat, message, and citation surfaces still boot from `apps/web/src/lib/mock-data.ts`. The stream submission path calls the backend, but the surrounding workspace/chat CRUD views need API-backed loading and mutation.

Required follow-up:

- Add `workspaces`, `chats`, `messages`, and `documents` API clients.
- Load initial data from the backend instead of local seed data.
- Add create/edit/delete flows for workspaces and chats.

### Authentication

`apps/api/app/core/auth.py` contains a demo-user bridge for local development. Production must verify Supabase JWTs and reject unauthenticated requests.

Required follow-up:

- Validate Supabase JWTs against JWKS.
- Remove demo headers from production builds.
- Keep backend ownership checks even when RLS is enabled.

### Embeddings

`apps/api/app/services/embeddings.py` uses an OpenAI-compatible remote embeddings client in production and keeps a deterministic fallback vector for tests or unconfigured local development. Retrieval quality depends on a valid `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and 768-dimensional embedding model.

Required follow-up:

- Add a backend health check that verifies embedding provider configuration without echoing secrets.
- Alert clearly when document ingestion falls back because the embedding provider is unavailable.
- Keep `EMBEDDING_BATCH_SIZE` modest on Render workers to avoid large request payloads and memory spikes.

### Background jobs

Celery has a local callable fallback and `memory_tasks.py` currently returns a queued marker for summarization.

Required follow-up:

- Run a real Celery worker against Redis.
- Implement chat summarization and summary embedding persistence.
- Persist job state into `background_jobs`.

### Document ingestion

Document upload and chunk persistence are present, but full document UX is not complete.

Required follow-up:

- Show document processing status from `GET /workspaces/{workspace_id}/documents`.
- Associate document chunks with `documents`/`document_chunks` consistently across migrations and runtime writes.
- Surface document citations in final answers.
