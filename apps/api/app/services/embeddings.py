from functools import lru_cache
import hashlib
import random
from typing import Protocol

import numpy as np

from app.core.config import Settings


class RemoteEmbeddingClient(Protocol):
    def embed(self, texts: list[str], *, model: str, dimensions: int) -> list[list[float]]:
        """Return provider-backed embeddings for the supplied texts."""


class OpenAIEmbeddingClient:
    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def embed(self, texts: list[str], *, model: str, dimensions: int) -> list[list[float]]:
        response = self._get_client().embeddings.create(
            input=texts,
            model=model,
            dimensions=dimensions,
        )
        return [item.embedding for item in response.data]


class EmbeddingService:
    def __init__(self, settings: Settings, remote_client: RemoteEmbeddingClient | None = None):
        self.settings = settings
        self._model = None
        self._remote_client = remote_client

    def _fallback_embedding(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed)
        values = np.array([rng.uniform(-1, 1) for _ in range(self.settings.embedding_dimensions)], dtype=np.float32)
        norm = np.linalg.norm(values) or 1.0
        return (values / norm).tolist()

    def _fallback_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self._fallback_embedding(text) for text in texts]

    def _remote_embeddings(self, texts: list[str]) -> list[list[float]]:
        api_key = self.settings.embedding_api_key or self.settings.llm_api_key
        if not api_key:
            return self._fallback_embeddings(texts)

        client = self._remote_client or OpenAIEmbeddingClient(
            api_key=api_key,
            base_url=self.settings.embedding_base_url,
        )
        try:
            return client.embed(
                texts,
                model=self.settings.embedding_model,
                dimensions=self.settings.embedding_dimensions,
            )
        except Exception:
            return self._fallback_embeddings(texts)

    def _local_embedding(self, text: str) -> list[float]:
        from sentence_transformers import SentenceTransformer

        if self._model is None:
            self._model = SentenceTransformer(self.settings.embedding_model)
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.astype(np.float32).tolist()

    def embed(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0] if vectors else self._fallback_embedding(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        provider = self.settings.embedding_provider.lower().strip()
        if provider in {"openai", "remote"}:
            return self._remote_embeddings(texts)
        if provider in {"local", "sentence-transformers", "sentence_transformers"}:
            return [self._safe_local_embedding(text) for text in texts]
        return self._fallback_embeddings(texts)

    def _safe_local_embedding(self, text: str) -> list[float]:
        try:
            return self._local_embedding(text)
        except Exception:
            return self._fallback_embedding(text)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    from app.core.config import get_settings

    return EmbeddingService(get_settings())
