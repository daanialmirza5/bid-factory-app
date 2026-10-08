from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbeddingService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            from sentence_transformers import SentenceTransformer

            if self._model is None:
                self._model = SentenceTransformer(self.model_name)
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return np.asarray(vectors, dtype=np.float32).tolist()
        except Exception as exc:
            raise RuntimeError(f"Unable to generate embeddings with model '{self.model_name}'.") from exc