import pytest

from app.db.session import configure_backend_connection


class FakeConnection:
    def __init__(self):
        self.executed = []

    async def execute(self, query):
        self.executed.append(query)


@pytest.mark.anyio
async def test_backend_connections_enable_service_context_for_rls_policies():
    conn = FakeConnection()

    await configure_backend_connection(conn)

    assert conn.executed == ["SET app.backend_service = 'on'"]
