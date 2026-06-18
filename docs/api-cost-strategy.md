# API Cost Strategy

The architecture assumes a strict OpenRouter budget, so the backend must measure and limit every expensive operation.

## Model Routing

- Cheap model: intent routing, title generation, short summaries.
- Primary model: final answer generation through OpenRouter.
- Fallback model: one lower-cost backup when the primary model fails.
- Local model: `BAAI/bge-base-en-v1.5` embeddings to avoid embedding API spend.
- Optional local reranker: `BAAI/bge-reranker-base` for higher-quality retrieval without LLM reranking calls.

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
