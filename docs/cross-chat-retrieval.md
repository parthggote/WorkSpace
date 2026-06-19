# Cross-Chat Retrieval

Cross-chat retrieval is the highest-priority feature. It lets a workspace remember relevant previous conversations without leaking context across workspaces.

## Ingestion

After each completed assistant turn:

```text
messages in chat
-> build rolling chat memory summary
-> store chat_sessions.summary and chat_sessions.last_summarized_at
-> embed summary with remote 768-dimensional embedding model
-> replace message_embeddings source_type='summary' for that chat
```

Individual user and assistant messages are still embedded as `source_type='chat'`. The summary row gives retrieval a stable chat-level memory target, while message embeddings remain a fallback for chats created before summary backfill or highly specific topic lookups.

The embedding dimension is fixed at 768 to match `message_embeddings.embedding vector(768)`. Production uses an OpenAI-compatible remote embeddings API instead of loading `sentence-transformers` locally.

## Query Flow

```text
query embedding
-> candidate chats in the same workspace, excluding the current chat
-> score candidates by summary embedding similarity, message embedding fallback, title match, lexical overlap, and recency
-> select top chats
-> fetch recent messages from selected chats
-> prompt builder with citation metadata
```

No vector query may run without a workspace filter. Cross-chat retrieval must also exclude the active chat so the message just saved in the current conversation cannot crowd out the intended prior conversation.

## Advanced Reranking

The reranker combines:

- vector similarity;
- keyword overlap;
- recency boost;
- chat title match;
- source type boost for summaries or document chunks;
- optional cross-encoder reranking only when the worker has enough memory and `ENABLE_CROSS_ENCODER_RERANKER=true`.

The database records both first-pass similarity and final rerank scores in `retrieval_results` so retrieval behavior can be debugged.

## Citation Metadata

When a previous chat is used, the final answer should cite:

- chat title;
- message id;
- timestamp;
- similarity score;
- rerank score.

Only cite prior chats selected by the chat-level scorer. Weak retrieval should be omitted rather than over-cited.

## Document Upload Reuse

Uploaded document chunks share the same embedding table and reranking path. They differ by `source_type='document'` and a `document_chunk_id`, which lets the citation builder show filename, page number, and chunk metadata.

Document ingestion runs in a Celery worker and embeds chunks in small batches using `EMBEDDING_BATCH_SIZE`. This avoids loading large local embedding models and keeps Render worker memory stable during uploads.
