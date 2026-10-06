import pytest

from indexmind.store import Chunk, ChunkStore


@pytest.fixture
def store() -> ChunkStore:
    return ChunkStore(":memory:")


def test_search_ranks_by_cosine_similarity(store: ChunkStore):
    store.replace_file(
        "a.md",
        "sig",
        [Chunk("a.md", "east"), Chunk("a.md", "north"), Chunk("a.md", "north-east")],
        [[1, 0], [0, 1], [1, 1]],
    )

    results = store.search([0, 2], k=2)

    assert [chunk.text for chunk, _ in results] == ["north", "north-east"]
    assert results[0][1] == pytest.approx(1.0)


def test_replacing_a_file_drops_its_old_chunks(store: ChunkStore):
    store.replace_file("a.md", "v1", [Chunk("a.md", "old")], [[1, 0]])
    store.replace_file("a.md", "v2", [Chunk("a.md", "new")], [[1, 0]])

    assert [c.text for c in store.all_chunks()] == ["new"]
    assert store.signatures() == {"a.md": "v2"}


def test_removing_a_file_drops_its_chunks(store: ChunkStore):
    store.replace_file("a.md", "v1", [Chunk("a.md", "a")], [[1, 0]])
    store.replace_file("b.md", "v1", [Chunk("b.md", "b")], [[0, 1]])

    store.remove_file("a.md")

    assert [c.path for c in store.all_chunks()] == ["b.md"]
    assert store.count() == 1


def test_search_on_empty_store_returns_nothing(store: ChunkStore):
    assert store.search([1, 0], k=3) == []


def test_store_persists_to_disk(tmp_path):
    db = tmp_path / "index.db"
    ChunkStore(db).replace_file("a.md", "v1", [Chunk("a.md", "kept", page=2)], [[1, 0]])

    reopened = ChunkStore(db)

    assert reopened.all_chunks()[0].page == 2


def test_location_includes_page_and_heading():
    chunk = Chunk("guide.pdf", "text", page=3, heading="Setup")

    assert chunk.location == "guide.pdf · p. 3 · Setup"
