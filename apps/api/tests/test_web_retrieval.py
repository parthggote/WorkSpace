import pytest

from app.core.config import Settings
from app.services.web_retrieval import WebRetrievalService


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "results": [
                {
                    "title": "Example result",
                    "url": "https://example.com/page",
                    "content": "A concise Tavily snippet.",
                    "score": 0.91,
                }
            ]
        }


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, json, headers):
        self.requests.append({"url": url, "json": json, "headers": headers})
        return FakeResponse()


@pytest.mark.anyio
async def test_search_uses_tavily_api_and_normalizes_results(monkeypatch):
    client = FakeClient()

    def fake_client_factory(*args, **kwargs):
        return client

    monkeypatch.setattr("app.services.web_retrieval.httpx.AsyncClient", fake_client_factory)

    service = WebRetrievalService(
        Settings(
            tavily_api_key="tvly-test",
            tavily_search_depth="basic",
            max_web_search_results=3,
        )
    )

    results = await service.search("latest ai news", count=5)

    assert client.requests[0]["url"] == "https://api.tavily.com/search"
    assert client.requests[0]["headers"] == {"Authorization": "Bearer tvly-test"}
    assert client.requests[0]["json"]["max_results"] == 3
    assert client.requests[0]["json"]["include_answer"] is False
    assert results == [
        {
            "title": "Example result",
            "url": "https://example.com/page",
            "description": "A concise Tavily snippet.",
            "content": "A concise Tavily snippet.",
            "score": 0.91,
            "source": "tavily",
        }
    ]
