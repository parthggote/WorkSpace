# Cross-Chat Retrieval

Cross-chat retrieval is the highest-priority feature. It lets a workspace remember relevant previous conversations without leaking context across workspaces.

## Ingestion

After saving a message:

```text
message -> chunk if needed -> embed with BAAI/bge-base-en-v1.5 -> message_embeddings
```

The embedding dimension is fixed at 768. Long assistant messages should be chunked into 500-800 token chunks with roughly 100 token overlap.

Chat summaries are embedded as `source_type='summary'` after every 20 messages or after a chat becomes inactive.

## Query Flow

```text
query embedding
-> pgvector top 20 filtered by workspace_id
-> advanced reranker
-> context compressor
-> top 5 memory chunks
-> prompt builder with citation metadata
```

No vector query may run without a workspace filter.

## Advanced Reranking

The reranker combines:

- vector similarity;
- keyword overlap;
- recency boost;
- chat title match;
- source type boost for summaries or document chunks;
- optional `BAAI/bge-reranker-base` cross-encoder score when `ENABLE_CROSS_ENCODER_RERANKER=true`.

The database records both first-pass similarity and final rerank scores in `retrieval_results` so retrieval behavior can be debugged.

## Citation Metadata

When a previous chat is used, the final answer should cite:

- chat title;
- message id;
- timestamp;
- similarity score;
- rerank score.

Only cite prior chats when relevance clears the configured threshold. Weak retrieval should be omitted rather than over-cited.

## Document Upload Reuse

Uploaded document chunks share the same embedding table and reranking path. They differ by `source_type='document'` and a `document_chunk_id`, which lets the citation builder show filename, page number, and chunk metadata.
