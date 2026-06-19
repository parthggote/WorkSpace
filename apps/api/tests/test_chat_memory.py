import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.chat_memory import (
    build_chat_memory_summary,
    retrieve_workspace_chat_context,
)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


def test_build_chat_memory_summary_uses_recent_user_and_assistant_messages():
    summary = build_chat_memory_summary(
        [
            {"role": "system", "content": "ignore"},
            {"role": "user", "content": "study of engineering"},
            {"role": "assistant", "content": "Engineering studies systems, design, and tradeoffs."},
        ]
    )

    assert "user: study of engineering" in summary
    assert "assistant: Engineering studies systems" in summary
    assert "system: ignore" not in summary


@pytest.mark.anyio
async def test_retrieve_workspace_chat_context_uses_named_chat_summary():
    pool = AsyncMock()
    workspace_id = str(uuid.uuid4())
    current_chat_id = str(uuid.uuid4())
    target_chat_id = uuid.uuid4()
    other_chat_id = uuid.uuid4()
    message_id = uuid.uuid4()

    pool.fetch.side_effect = [
        [
            {
                "id": other_chat_id,
                "title": "New chat",
                "summary": "unrelated packaging discussion",
                "updated_at": datetime.now(timezone.utc),
                "similarity": 0.10,
            },
            {
                "id": target_chat_id,
                "title": "chat101",
                "summary": "study of engineering and technical systems",
                "updated_at": datetime.now(timezone.utc),
                "similarity": 0.20,
            },
        ],
        [],
        [
            {
                "id": message_id,
                "role": "user",
                "content": "Study of engineering covers designing reliable systems.",
                "created_at": datetime.now(timezone.utc),
            }
        ],
    ]

    chunks = await retrieve_workspace_chat_context(
        pool,
        FakeEmbeddingService(),
        workspace_id,
        current_chat_id,
        "find from the chat101",
        top_chats=1,
    )

    assert len(chunks) == 1
    assert chunks[0]["chat_id"] == str(target_chat_id)
    assert chunks[0]["chat_title"] == "chat101"
    assert "Study of engineering" in chunks[0]["content"]


@pytest.mark.anyio
async def test_retrieve_workspace_chat_context_uses_recent_chat_for_last_conversation():
    pool = AsyncMock()
    workspace_id = str(uuid.uuid4())
    current_chat_id = str(uuid.uuid4())
    recent_chat_id = uuid.uuid4()
    older_chat_id = uuid.uuid4()
    message_id = uuid.uuid4()

    pool.fetch.side_effect = [
        [
            {
                "id": recent_chat_id,
                "title": "Engineering notes",
                "summary": "study of engineering",
                "updated_at": datetime.now(timezone.utc),
                "similarity": 0.05,
            },
            {
                "id": older_chat_id,
                "title": "Older chat",
                "summary": "unrelated",
                "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "similarity": 0.90,
            },
        ],
        [],
        [
            {
                "id": message_id,
                "role": "assistant",
                "content": "Engineering is the practical study of building systems.",
                "created_at": datetime.now(timezone.utc),
            }
        ],
    ]

    chunks = await retrieve_workspace_chat_context(
        pool,
        FakeEmbeddingService(),
        workspace_id,
        current_chat_id,
        "give me the summary from my last conversation",
        top_chats=1,
    )

    assert len(chunks) == 1
    assert chunks[0]["chat_id"] == str(recent_chat_id)


@pytest.mark.anyio
async def test_retrieve_workspace_chat_context_uses_message_embeddings_when_summary_missing():
    pool = AsyncMock()
    workspace_id = str(uuid.uuid4())
    current_chat_id = str(uuid.uuid4())
    target_chat_id = uuid.uuid4()
    recent_chat_id = uuid.uuid4()
    message_id = uuid.uuid4()

    pool.fetch.side_effect = [
        [
            {
                "id": recent_chat_id,
                "title": "Recent unrelated chat",
                "summary": None,
                "updated_at": datetime.now(timezone.utc),
                "similarity": None,
            },
            {
                "id": target_chat_id,
                "title": "Engineering study",
                "summary": None,
                "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "similarity": None,
            },
        ],
        [
            {
                "chat_id": target_chat_id,
                "similarity": 0.95,
            }
        ],
        [
            {
                "id": message_id,
                "role": "user",
                "content": "Study of engineering includes mechanics, systems, and design.",
                "created_at": datetime.now(timezone.utc),
            }
        ],
    ]

    chunks = await retrieve_workspace_chat_context(
        pool,
        FakeEmbeddingService(),
        workspace_id,
        current_chat_id,
        "what did we discuss about engineering study?",
        top_chats=1,
    )

    assert len(chunks) == 1
    assert chunks[0]["chat_id"] == str(target_chat_id)
