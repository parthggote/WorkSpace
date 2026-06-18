# Web Retrieval

The project uses Tavily Search for URL discovery and search snippets. The backend can still perform safe page fetching, extraction, ranking, reranking, compression, and citation construction itself.

## Pipeline

```text
intent router
-> Tavily Search candidate URLs and snippets
-> backend http fetch
-> readable text extraction
-> chunk and rank
-> rerank against user query
-> compress to top snippets
-> prompt builder
-> citations
```

Do not use built-in LLM browsing plugins or answer APIs that browse and answer on behalf of the app.

## Limits

- Search results: 5
- Pages fetched: 3
- Page timeout: 8-10 seconds
- Extracted text per page: 4,000-6,000 characters
- Web snippets sent to the LLM: 3
- Redis cache TTL: 15 minutes for search and extraction results

## Redis Use

Redis stores:

- Tavily search results keyed by query hash;
- page extraction results keyed by normalized URL hash;
- request deduplication locks;
- per-user and per-workspace search rate limits.

## Citations

`web_sources` stores title, URL, snippet, extracted text hash, rank score, rerank score, and retrieval time. Assistant messages reference these rows when live sources support the answer.

## Fallbacks

If Tavily fails, use a cached result when available. If page fetch fails, use the Tavily snippet and try the next URL. If no live sources are available, the assistant should say live retrieval was unavailable and avoid fabricating citations.
