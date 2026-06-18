import json
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from fastapi import HTTPException, status

from app.core.config import Settings


class RedisService:
    def __init__(self, settings: Settings):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    async def get_json(self, key: str):
        try:
            value = await self.client.get(key)
        except Exception:
            return None
        return json.loads(value) if value else None

    async def set_json(self, key: str, value, ttl_seconds: int) -> None:
        try:
            await self.client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception:
            return None

    async def cached(self, key: str, ttl_seconds: int, loader: Callable[[], Awaitable]):
        existing = await self.get_json(key)
        if existing is not None:
            return existing
        value = await loader()
        await self.set_json(key, value, ttl_seconds)
        return value

    async def enforce_limit(self, key: str, limit: int, window_seconds: int) -> None:
        try:
            count = await self.client.incr(key)
            if count == 1:
                await self.client.expire(key, window_seconds)
            if count > limit:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
        except HTTPException:
            raise
        except Exception:
            return None
