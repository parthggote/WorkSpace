# Streaming

Streaming uses Server-Sent Events from the FastAPI backend.

## Endpoint

```text
POST /chat/stream
```

Payload:

```json
{
  "workspace_id": "uuid",
  "chat_id": "uuid",
  "message": "user query"
}
```

## Event Contract

```json
{ "type": "status", "content": "Checking workspace memory..." }
```

```json
{ "type": "status", "content": "Searching live web..." }
```

```json
{ "type": "reasoning_summary", "content": "Found related context from a previous chat." }
```

```json
{ "type": "answer_delta", "content": "The answer is..." }
```

```json
{ "type": "citations", "content": [] }
```

```json
{ "type": "done" }
```

## Safety

The app streams safe status and reasoning summaries, not hidden chain-of-thought. Status events may describe backend actions and high-level findings, but they must not expose private model deliberation.

## Persistence

The backend should persist:

- user message before orchestration starts;
- assistant message after generation completes or fails with partial content;
- web citations and memory citations attached to the assistant message;
- usage logs and tool call logs for each provider/tool step.

## Failure Handling

If retrieval fails, stream a status event and continue with available context. If the LLM stream fails after partial output, persist the partial assistant message and send an error event that the UI can show without losing the chat state.
