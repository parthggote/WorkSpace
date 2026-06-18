# API Cost Strategy

The architecture assumes a strict OpenRouter budget, so the backend must measure and limit every expensive operation.

## Model Routing

- Cheap model: intent routing, title generation, short summaries.
- Primary model: final answer generation through OpenRouter.
- Fallback model: one lower-cost backup when the primary model fails.
- Embedding model: `text-embedding-3-small` or `openai/text-embedding-3-small` through an OpenAI-compatible remote embeddings API.
- Optional reranker: keep the deterministic lightweight reranker by default; only enable heavy cross-encoder reranking on a larger worker.

## Embedding Cost and Memory Decision

The project previously planned local sentence-transformer embeddings. That avoids API spend but loads a PyTorch stack into the worker, which can exhaust memory during document ingestion on small Render instances.

The current production decision is remote batched embeddings:

- no local model weights in API or worker memory;
- stable document ingestion on small instances;
- `768` dimensions to match the existing pgvector schema;
- configurable OpenAI-compatible base URL, so either direct OpenAI or OpenRouter can be used.

Use `EMBEDDING_BATCH_SIZE` to control request and memory pressure. Keep it modest, such as `24`, for Render starter-sized workers.

## Hard Limits

- Max memory candidates before rerank: 20
- Max memory chunks after rerank: 5
- Max web sources in prompt: 3
- Max pages fetched: 3
- Max output tokens: 700-900
- Max LLM retries: 1
- Max controlled tool calls per request: 3-5

## Redis Cost Controls

Redis should hold:

- per-user request counters;
- per-workspace request counters;
- model usage counters;
- embedding request counters;
- Tavily query cache;
- page extraction cache;
- duplicate in-flight request locks.

## Usage Logging

Every provider call writes to `usage_logs`:

- workspace id;
- chat id;
- model;
- provider;
- prompt tokens;
- completion tokens;
- total tokens;
- estimated cost;
- latency;
- status.

The app should fail closed when a workspace or user crosses configured demo limits.
