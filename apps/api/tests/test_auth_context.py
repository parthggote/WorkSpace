from types import SimpleNamespace

import pytest

from app.core.auth import get_current_user


class FakeConnection:
    def __init__(self):
        self.executed = []
        self.fetchrow_calls = []

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "supabase_user_id": args[0],
            "email": args[1],
        }


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.connection = FakeConnection()

    def acquire(self):
        return FakeAcquire(self.connection)


@pytest.mark.anyio
async def test_demo_user_sets_postgres_auth_context_before_upsert():
    pool = FakePool()
    request = SimpleNamespace(
        headers={
            "x-demo-user-id": "00000000-0000-0000-0000-000000000001",
            "x-demo-email": "demo@example.com",
        },
        app=SimpleNamespace(state=SimpleNamespace(db_pool=pool)),
    )

    user = await get_current_user(request)

    assert user.supabase_user_id == "00000000-0000-0000-0000-000000000001"
    assert pool.connection.executed == [
        (
            "SELECT set_config('request.jwt.claim.sub', $1, true)",
            ("00000000-0000-0000-0000-000000000001",),
        )
    ]
    assert "INSERT INTO users" in pool.connection.fetchrow_calls[0][0]
