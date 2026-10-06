import os

import pytest

from indexmind.indexer import Indexer
from indexmind.store import ChunkStore


@pytest.fixture
def docs(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "guide.md").write_text("# Setup\nInstall the app.\n# Usage\nOpen the app.")
    (folder / "nested").mkdir()
    (folder / "nested" / "notes.txt").write_text("Remember the milk.")
    (folder / "image.png").write_bytes(b"\x89PNG")
    return folder


@pytest.fixture
def indexer(docs, embedder):
    return Indexer(docs, ChunkStore(":memory:"), embedder, chunk_size=500, chunk_overlap=50)


async def test_sync_indexes_supported_files_recursively(indexer):
    status = await indexer.sync()

    assert status.state == "idle"
    assert status.files == 2
    assert status.chunks == 3
    assert status.processed == 2


async def test_second_sync_skips_unchanged_files(indexer, embedder):
    await indexer.sync()
    calls = embedder.calls

    status = await indexer.sync()

    assert embedder.calls == calls
    assert status.processed == 0


async def test_sync_picks_up_changed_and_deleted_files(indexer, docs):
    await indexer.sync()
    guide = docs / "guide.md"
    guide.write_text("# Only\nOne section now, and it is longer.")
    stat = guide.stat()
    os.utime(guide, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    (docs / "nested" / "notes.txt").unlink()

    status = await indexer.sync()

    assert status.files == 1
    assert status.chunks == 1


async def test_unreadable_file_is_reported_without_stopping_the_run(indexer, docs):
    (docs / "broken.pdf").write_bytes(b"not a pdf")

    status = await indexer.sync()

    assert "broken.pdf" in status.failures
    assert status.files == 2


async def test_missing_folder_indexes_nothing(tmp_path, embedder):
    indexer = Indexer(
        tmp_path / "absent", ChunkStore(":memory:"), embedder, chunk_size=500, chunk_overlap=50
    )

    status = await indexer.sync()

    assert status.files == 0
