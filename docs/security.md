# Security

Security is centered on workspace isolation, secret hygiene, cost controls, and safe streaming.

## Workspace Isolation

No backend function should accept a `chat_id`, `message_id`, `document_id`, or embedding id without also validating the owning `workspace_id`.

Vector search must always filter by workspace before reranking. Reranking cannot fix a cross-workspace leak after candidates have already been fetched.

## Secret Hygiene

Never commit real `.env` files. Commit only `.env.example` placeholders.

Secrets must live in:

- local developer `.env` files ignored by Git;
- Supabase project settings;
- Vercel environment variables;
- Render or Railway environment variables;
- Upstash credentials;
- provider dashboards.

Do not log:

- JWTs;
- Supabase service role keys;
- OpenRouter keys;
- Tavily keys;
- Redis URLs with passwords;
- raw uploaded document contents unless explicitly in a secure debug environment.

## Upload Safety

Document upload should enforce:

- workspace ownership before storage;
- file size limits;
- MIME type allowlist;
- extracted text length limits;
- background processing through the job queue;
- citation metadata that points to document chunks, not raw private files.

## Rate Limits

Redis-backed limits should cover:

- chat requests per user;
- chat requests per workspace;
- Tavily Search requests;
- document upload count and size;
- background job enqueue rate;
- total demo token spend.

## Prompt Safety

Web pages and uploaded documents are untrusted input. The prompt builder must label them as retrieved sources and prevent source text from overriding system instructions.
