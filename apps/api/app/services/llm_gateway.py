from collections.abc import AsyncIterator
from typing import Any
from openai import AsyncOpenAI

from app.core.config import Settings


class LLMGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.llm_api_key or "missing", base_url=settings.llm_base_url)

    async def stream_answer(self, messages: list[dict[str, str]]) -> AsyncIterator[Any]:
        if not self.settings.llm_api_key:
            demo = "Demo mode: configure LLM_API_KEY to receive model output. The retrieval and streaming pipeline is wired."
            for token in demo.split(" "):
                yield token + " "
            return

        stream = await self.client.chat.completions.create(
            model=self.settings.default_model,
            messages=messages,
            max_tokens=self.settings.max_output_tokens,
            temperature=0.3,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if getattr(chunk, "usage", None):
                yield {"usage": chunk.usage.total_tokens}
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

