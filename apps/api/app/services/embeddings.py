from functools import lru_cache
import hashlib
import random

import numpy as np

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def _fallback_embedding(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed)
        values = np.array([rng.uniform(-1, 1) for _ in range(768)], dtype=np.float32)
        norm = np.linalg.norm(values) or 1.0
        return (values / norm).tolist()

    def embed(self, text: str) -> list[float]:
        try:
            from sentence_transformers import SentenceTransformer

            if self._model is None:
                self._model = SentenceTransformer(self.settings.embedding_model)
            vector = self._model.encode(text, normalize_embeddings=True)
            return vector.astype(np.float32).tolist()
        except Exception:
            return self._fallback_embedding(text)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    from app.core.config import get_settings

    return EmbeddingService(get_settings())

