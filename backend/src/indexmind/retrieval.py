"""Hybrid retrieval: vector and keyword rankings merged with reciprocal rank fusion."""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass

from indexmind.keyword import BM25Index
from indexmind.llm import Embedder
from indexmind.store import Chunk, ChunkStore


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Hashable]], k: int = 60
) -> list[tuple[Hashable, float]]:
    """Combine ranked lists; an item scores sum(1 / (k + rank)) over the lists it appears in."""
    scores: dict[Hashable, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    similarity: float  # cosine similarity from vector search, 0 if only matched by keyword
    score: float  # fused score used for ordering


class Retriever:
    def __init__(self, store: ChunkStore, embedder: Embedder, candidates: int = 20) -> None:
        self._store = store
        self._embedder = embedder
        self._candidates = candidates
        self._keyword: tuple[int, BM25Index, list[Chunk]] | None = None

    def invalidate(self) -> None:
        self._keyword = None

    async def retrieve(self, query: str, k: int) -> list[Hit]:
        [query_vector] = await self._embedder.embed([query])
        dense = self._store.search(query_vector, self._candidates)
        similarity = {chunk.id: score for chunk, score in dense}

        chunks, index = self._keyword_index()
        by_id = {chunk.id: chunk for chunk in chunks}
        sparse_ids = [chunks[i].id for i, _ in index.search(query, self._candidates)]

        fused = reciprocal_rank_fusion([[c.id for c, _ in dense], sparse_ids])
        return [
            Hit(chunk=by_id[chunk_id], similarity=similarity.get(chunk_id, 0.0), score=score)
            for chunk_id, score in fused[:k]
        ]

    def _keyword_index(self) -> tuple[list[Chunk], BM25Index]:
        count = self._store.count()
        if self._keyword is None or self._keyword[0] != count:
            chunks = self._store.all_chunks()
            texts = [f"{c.heading or ''}\n{c.text}" for c in chunks]
            self._keyword = (count, BM25Index(texts), chunks)
        return self._keyword[2], self._keyword[1]
