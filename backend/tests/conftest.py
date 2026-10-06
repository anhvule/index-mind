import hashlib

import pytest


class FakeEmbedder:
    """Deterministic bag-of-words embedding: texts sharing words get similar vectors."""

    dims = 64

    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        return [self._vector(text) for text in texts]

    def _vector(self, text):
        vector = [0.0] * self.dims
        for word in text.lower().split():
            bucket = int(hashlib.md5(word.strip(".,?!").encode()).hexdigest(), 16) % self.dims
            vector[bucket] += 1.0
        return vector


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()
