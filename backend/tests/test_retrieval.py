import pytest

from indexmind.retrieval import Retriever, reciprocal_rank_fusion
from indexmind.store import Chunk, ChunkStore


def test_rrf_rewards_items_ranked_well_in_both_lists():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "a"]])

    assert [item for item, _ in fused][0] == "b"


def test_rrf_keeps_items_found_by_one_list_only():
    fused = dict(reciprocal_rank_fusion([["a"], ["b"]]))

    assert set(fused) == {"a", "b"}


class KeywordOnlyEmbedder:
    """Every text gets the same vector, so only BM25 can tell chunks apart."""

    async def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


@pytest.fixture
def store() -> ChunkStore:
    store = ChunkStore(":memory:")
    texts = ["holiday allowance is 25 days", "the office opens at 9", "parking is free"]
    store.replace_file("a.md", "v1", [Chunk("a.md", t) for t in texts], [[1.0, 0.0]] * 3)
    return store


async def test_keyword_match_lifts_exact_term_to_the_top(store):
    retriever = Retriever(store, KeywordOnlyEmbedder())

    hits = await retriever.retrieve("parking", k=2)

    assert hits[0].chunk.text == "parking is free"
    assert hits[0].similarity == pytest.approx(1.0)


async def test_keyword_index_refreshes_after_store_changes(store):
    retriever = Retriever(store, KeywordOnlyEmbedder())
    await retriever.retrieve("parking", k=1)

    store.replace_file("b.md", "v1", [Chunk("b.md", "bicycle storage in basement")], [[1.0, 0.0]])
    hits = await retriever.retrieve("bicycle", k=1)

    assert hits[0].chunk.path == "b.md"
