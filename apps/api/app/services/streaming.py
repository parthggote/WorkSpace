import json
from collections.abc import AsyncIterator


def sse_event(event_type: str, content) -> str:
    payload = content if isinstance(content, dict) else {"content": content}
    payload = {"type": event_type, **payload}
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


async def emit(event_type: str, content) -> AsyncIterator[str]:
    yield sse_event(event_type, content)
