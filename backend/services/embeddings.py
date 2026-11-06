from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbeddingService:
    """Sentence-transformer embeddings on ONNX Runtime.

    This runs the same model without PyTorch, so the API fits in a 512 MB container.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            from fastembed import TextEmbedding

            if self._model is None:
                name = self.model_name if "/" in self.model_name else f"sentence-transformers/{self.model_name}"
                self._model = TextEmbedding(model_name=name)
            vectors = np.asarray(list(self._model.embed(texts)), dtype=np.float32)
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            return (vectors / np.clip(norms, 1e-12, None)).tolist()
        except Exception as exc:
            raise RuntimeError(f"Unable to generate embeddings with model '{self.model_name}'.") from exc
