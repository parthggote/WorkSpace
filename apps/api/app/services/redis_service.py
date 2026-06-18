"""Redis wiring for cache, rate limits, and lightweight task state."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> str | bytes | None:
        """Read a raw value."""

    def set(self, key: str, value: str, ex: int | None = None) -> Any:
        """Set a raw value with optional TTL."""

    def incr(self, key: str) -> int:
        """Increment a numeric value."""

    def expire(self, key: str, seconds: int) -> Any:
        """Set key expiry."""


@dataclass(frozen=True)
class RedisSettings:
    url: str | None = None
    namespace: str = "ai-chat"
    default_ttl_seconds: int = 900

    @classmethod
    def from_env(cls) -> "RedisSettings":
        return cls(
            url=os.getenv("REDIS_URL"),
            namespace=os.getenv("REDIS_NAMESPACE", "ai-chat"),
            default_ttl_seconds=int(os.getenv("REDIS_DEFAULT_TTL_SECONDS", "900")),
        )


class InMemoryRedis:
    """Small Redis-compatible fallback for local tests and missing dependencies."""

    def __init__(self) -> None:
        self._values: dict[str, tuple[str, float | None]] = {}

    def get(self, key: str) -> str | None:
        record = self._values.get(key)
        if record is None:
            return None
        value, expires_at = record
        if expires_at is not None and expires_at < time.time():
            self._values.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        expires_at = time.time() + ex if ex else None
        self._values[key] = (value, expires_at)
        return True

    def incr(self, key: str) -> int:
        current = self.get(key)
        next_value = int(current or "0") + 1
        self.set(key, str(next_value))
        return next_value

    def expire(self, key: str, seconds: int) -> bool:
        current = self.get(key)
        if current is None:
            return False
        self.set(key, current, ex=seconds)
        return True


def build_redis_client(settings: RedisSettings | None = None) -> CacheBackend:
    settings = settings or RedisSettings.from_env()
    if not settings.url:
        return InMemoryRedis()

    try:
        from redis import Redis  # type: ignore

        return Redis.from_url(settings.url, decode_responses=True)
    except Exception:
        return InMemoryRedis()


class RedisService:
    def __init__(
        self,
        *,
        client: CacheBackend | None = None,
        settings: RedisSettings | None = None,
    ) -> None:
        self.settings = settings or RedisSettings.from_env()
        self.client = client or build_redis_client(self.settings)

    def key(self, *parts: object) -> str:
        safe_parts = [str(part).strip().replace(" ", "-") for part in parts if part is not None]
        return ":".join([self.settings.namespace, *safe_parts])

    def get_json(self, key: str) -> Any | None:
        raw = self.client.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.settings.default_ttl_seconds
        self.client.set(key, json.dumps(value, default=str), ex=ttl)

    def check_rate_limit(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        count = self.client.incr(key)
        if count == 1:
            self.client.expire(key, window_seconds)
        return count <= limit, count

    def mark_task_state(self, task_id: str, state: str, payload: dict[str, Any] | None = None) -> None:
        self.set_json(
            self.key("task", task_id),
            {"state": state, "payload": payload or {}, "updated_at": int(time.time())},
            ttl_seconds=86400,
        )

    def get_task_state(self, task_id: str) -> dict[str, Any] | None:
        value = self.get_json(self.key("task", task_id))
        return value if isinstance(value, dict) else None

