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

`apps/api/app/services/embeddings.py` includes a deterministic fallback vector when the local embedding model cannot load. This is useful for import tests, but retrieval quality depends on loading the configured BGE model.

Required follow-up:

- Preload or health-check the embedding model at worker startup.
- Fail document ingestion clearly if production embeddings cannot run.

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

