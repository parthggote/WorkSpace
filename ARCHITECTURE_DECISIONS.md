# AI Workspace: Architectural Decisions & Technical Documentation

This document provides a comprehensive overview of the architectural, design, and engineering decisions made during the development of the AI Workspace platform. Every choice was optimized for performance, scalability, security, and developer ergonomics.

---

## 1. UI/UX Design

**Component Library:** **Shadcn UI** integrated natively with **Tailwind CSS**.

**Reasoning & Tradeoffs:**
When evaluating the frontend stack, we considered heavier component libraries like Material-UI (MUI) and Ant Design. However, these libraries often ship with immense JavaScript bundles and rely heavily on runtime CSS-in-JS (like Emotion or Styled Components). This creates a performance overhead that directly conflicts with Next.js Server Components.
- **Why Shadcn?** Shadcn is not a traditional npm dependency; instead, it provides highly accessible, unstyled Radix UI primitives that are directly copied into our codebase. This gives us 100% ownership of the code, allowing us to deeply customize the UI using zero-runtime Tailwind CSS utility classes. 
- **Aesthetics & Navigation:** We opted for a premium, minimalist grayscale aesthetic to ensure the focus remains on the AI's content rather than distracting UI chrome. We utilized the Next.js 14 App Router to ensure navigation between workspaces is fast and stateful, preventing full page reloads and keeping the heavy LLM chat context fully isolated by route.

---

## 2. Agentic Framework

**Framework Selected:** **LangGraph** (leveraging the broader LangChain ecosystem).

**Tradeoffs Considered:**
- *LangChain (Standard Chains):* While excellent for linear pipelines (e.g., prompt -> LLM -> output), standard chains are incredibly rigid. They struggle with cyclic operations where an agent might need to search, realize it needs more info, and search again before answering.
- *LlamaIndex:* Outstanding for building highly optimized RAG (Retrieval-Augmented Generation) pipelines over static documents, but it lacks the robust, flexible state-machine orchestration needed for a dynamic, multi-tool agent.
- *Vanilla OpenAI Functions:* Writing custom agent loops from scratch is tedious and error-prone when handling state persistence across multiple steps.

**Reasoning for LangGraph:**
LangGraph models the agent's workflow as a stateful, cyclic graph. It explicitly separates nodes into distinct computational steps (e.g., "Agent Node", "Tool Node"). This graph-based state machine allows the backend to precisely control execution, persist conversational memory effortlessly, and recover from tool errors by routing back to the reasoning node. It is the perfect balance between raw control and ecosystem support.

---

## 3. Streaming Architecture

**Implementation:** Real-time Server-Sent Events (SSE) via **FastAPI's `StreamingResponse`** paired with LangGraph's async streaming API.

**How it Works & Reasoning:**
Modern AI applications feel sluggish without real-time streaming. Waiting 10 seconds for a comprehensive answer is poor UX. We implemented a unidirectional SSE stream from the FastAPI backend to the Next.js frontend.
- **Separating Reasoning from Output:** Because we use LangGraph, our backend doesn't just stream raw text; it streams *state transitions*. When the agent decides to use a tool (like searching the web), the backend yields a `tool_call` event packet. When the LLM finally generates its answer, it yields `message_chunk` packets.
- **UI Reflection:** The React frontend parses these JSON packets in real-time. If it detects a `tool_call` (e.g., "Searching for 2026 World Cup scores"), it renders this inside a distinct, collapsible gray "Reasoning Block". Only the `message_chunk` tokens are appended to the primary conversational chat bubble. This guarantees that the user can peek into the agent's "thought process" without cluttering the final, polished answer.

---

## 4. Web Connectivity

**Implementation:** Live data retrieval via the **Tavily Search API**.

**Reasoning & Tradeoffs:**
To give the agent access to real-time information (e.g., live sports scores, current events), it needed web access. We considered building custom scraping tools using headless browsers (like Puppeteer or Playwright) or generic search APIs (like Google Custom Search).
- **Why Avoid Headless Browsers?** Running Playwright on a backend server is incredibly memory-intensive, slow to spin up, and frequently blocked by modern anti-bot captchas (Cloudflare).
- **Why Tavily?** Tavily is a search engine built *specifically* for LLM consumption. Instead of returning raw HTML that requires heavy parsing and chunking, Tavily handles the scraping, bypasses captchas, and instantly returns clean, concise markdown strings summarizing the most relevant data. This reduces latency from seconds to milliseconds and drastically saves on LLM context token limits.

---

## 5. Cross-Chat Context Retrieval

**Architecture:** 
- **Database:** Supabase with the `pgvector` extension.
- **Embedding Model:** remote 768-dimensional embeddings via an OpenAI-compatible embeddings API (`text-embedding-3-small` directly, or `openai/text-embedding-3-small` through OpenRouter).

**Retrieval Strategy:**
To give the agent a "long-term memory" across different workspaces, we implemented an asynchronous semantic retrieval system.
1. **Embedding:** When a conversation ends or reaches a significant milestone, a background Celery worker extracts the core facts, generates vector embeddings using the configured remote embeddings provider, and stores them in PostgreSQL/pgvector-backed embedding tables.
2. **Retrieval:** When a user asks a question in a new chat, the system performs a cosine-similarity vector search against their past workspaces.
3. **Surfacing Citations:** The vector database returns the top-K relevant contexts along with their metadata (Source Chat ID, Date, Title). This text is injected into the LangGraph system prompt. The LLM is explicitly instructed via its prompt to append markdown links pointing to these source IDs (e.g., `[Reference](workspace-id)`). The frontend intercepts these specific links and renders them as clickable UI citation pills, allowing the user to seamlessly jump back to the old conversation.

---

## 6. Authentication

**Decision:** **Yes**, robust authentication was implemented using **Supabase Auth**.

**Reasoning:**
For a prototype, auth is often skipped, but for an AI Workspace platform, it is an absolute architectural requirement for three critical reasons:
1. **Data Security & RLS:** Workspaces inherently contain sensitive, proprietary user data. By authenticating users, we leverage PostgreSQL Row-Level Security (RLS) policies tied directly to the Supabase JWT. This guarantees at the database level that a user can *only* query their own chat history and vectors.
2. **Context Isolation:** If authentication was skipped, cross-chat retrieval would query the entire global vector database, resulting in the agent hallucinating or leaking one user's private data into another user's chat.
3. **Financial Protection:** Enforcing the API usage caps ($8) is impossible without mapping token consumption to a unique, verified identity. We support both Google SSO (for frictionless onboarding) and standard Email/Password fallback.

---

## 7. API Cost Management

**Implementation:** Model routing via **OpenRouter** and strict backend database tracking.

**Strategy to Enforce the $8 Cap:**
- **Dynamic Model Routing:** We default the system to utilize highly capable but extremely cheap models (such as `openai/gpt-4o-mini` or `google/gemini-flash-1.5-8b`) for standard conversational interactions and tool routing. We only invoke expensive frontier models if the task complexity strictly demands it, drastically reducing the burn rate.
- **Precise Usage Tracking:** LangGraph natively supports tracking token usage metrics from OpenRouter. We configured the LLM client with `stream_options={"include_usage": True}`. At the conclusion of every stream, the exact prompt and completion token counts are captured.
- **Real-time Enforcement:** The backend calculates the micro-cent cost based on the specific model used and logs it asynchronously to a `usage_logs` PostgreSQL table mapped to the User ID. A specialized FastAPI middleware checks this running total before initiating any new LLM request. If the user hits the $8.00 cap, the API immediately halts and returns a `402 Payment Required` error, which the UI handles gracefully.

---

## 8. Embedding and Worker Memory Decision

**Decision:** Production embeddings are remote and OpenAI-compatible, not local `sentence-transformers`.

**Reasoning:** The local sentence-transformer/PyTorch stack can exhaust memory on small Render instances during document ingestion. The current architecture keeps the API and Celery worker lightweight by batching document chunks and sending them to a remote embeddings endpoint.

**Configuration:**

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=768
EMBEDDING_BATCH_SIZE=24
```

When using OpenRouter for embeddings, the provider remains `openai` because the code path means "OpenAI-compatible client":

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_MODEL=openai/text-embedding-3-small
```

The database remains on `vector(768)`, so this decision does not require a pgvector schema migration. Render worker deployment should keep concurrency low and recycle child tasks to avoid memory buildup:

```bash
python -m celery -A app.jobs.celery_app worker --loglevel=info --pool=solo --concurrency=1 --prefetch-multiplier=1 --max-tasks-per-child=10
```

---

## 9. Deployment and Runtime Boundaries

**Decision:** Deploy the frontend on **Vercel**, the FastAPI backend on **Render**, and the Celery worker as a separate **Render worker/web service** backed by Redis.

**Reasoning:**
- **Vercel for frontend:** Next.js App Router, shadcn UI, Supabase browser auth, and streaming chat UX fit Vercel's deployment model cleanly.
- **Render for backend:** FastAPI, Celery, document extraction, and Python AI orchestration need a long-running Python runtime rather than Vercel serverless functions.
- **Separate worker process:** Document upload, text extraction, chunking, and embeddings should not compete with live chat requests in the API process.
- **Supabase for state:** Supabase owns Auth, Postgres, pgvector, RLS, and Storage. The backend still performs ownership checks before accessing workspace-scoped resources.
- **Upstash/Redis-compatible Redis:** Redis is used for Celery broker/result channels, cache, rate limits, and lightweight stream state.

**Production environment shape:**

```env
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWKS_URL=
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
TAVILY_API_KEY=
LLM_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openai/gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIMENSIONS=768
EMBEDDING_BATCH_SIZE=24
```

No `.env` files, API keys, service-role keys, JWT secrets, or assignment documents should be committed. Secrets belong only in local ignored files or hosting-provider secret stores.

