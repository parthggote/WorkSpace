from app.core.config import Settings
from app.services.embeddings import EmbeddingService


class FakeRemoteEmbeddingClient:
    def __init__(self) -> None:
        self.calls = []

    def embed(self, texts: list[str], *, model: str, dimensions: int) -> list[list[float]]:
        self.calls.append({"texts": texts, "model": model, "dimensions": dimensions})
        return [[0.1] * dimensions for _ in texts]


def test_openai_provider_uses_remote_embedding_client() -> None:
    client = FakeRemoteEmbeddingClient()
    settings = Settings(
        embedding_provider="openai",
        embedding_api_key="test-key",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=768,
    )

    service = EmbeddingService(settings, remote_client=client)

    vector = service.embed("workspace context")

    assert len(vector) == 768
    assert client.calls == [
        {
            "texts": ["workspace context"],
            "model": "text-embedding-3-small",
            "dimensions": 768,
        }
    ]


def test_openai_provider_without_key_falls_back_to_deterministic_vector() -> None:
    settings = Settings(
        embedding_provider="openai",
        embedding_api_key="",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=768,
    )

    service = EmbeddingService(settings)

    first = service.embed("same text")
    second = service.embed("same text")

    assert len(first) == 768
    assert first == second
