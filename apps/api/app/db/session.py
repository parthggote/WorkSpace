from collections.abc import AsyncIterator
import asyncpg
from fastapi import Request


async def configure_backend_connection(conn) -> None:
    await conn.execute("SET app.backend_service = 'on'")


async def connect_pool(database_url: str) -> asyncpg.Pool | None:
    if not database_url:
        return None
    return await asyncpg.create_pool(database_url, min_size=1, max_size=8, init=configure_backend_connection)


async def get_pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return pool


async def transaction(pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
