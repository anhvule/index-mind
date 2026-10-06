"""Keeps the chunk store in sync with the documents folder."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from indexmind.chunking import chunk_text
from indexmind.documents import is_supported, read_sections
from indexmind.llm import Embedder
from indexmind.store import Chunk, ChunkStore

log = logging.getLogger(__name__)


@dataclass
class IndexStatus:
    state: Literal["idle", "indexing", "error"] = "idle"
    files: int = 0
    chunks: int = 0
    processed: int = 0
    pending: int = 0
    current: str | None = None
    failures: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


class Indexer:
    def __init__(
        self,
        docs_dir: Path,
        store: ChunkStore,
        embedder: Embedder,
        *,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self.docs_dir = docs_dir
        self._store = store
        self._embedder = embedder
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._lock = asyncio.Lock()
        self.status = IndexStatus(files=len(store.signatures()), chunks=store.count())

    def scan(self) -> dict[str, Path]:
        if not self.docs_dir.is_dir():
            return {}
        return {
            path.relative_to(self.docs_dir).as_posix(): path
            for path in sorted(self.docs_dir.rglob("*"))
            if is_supported(path)
        }

    async def sync(self) -> IndexStatus:
        """Index new and changed files and forget deleted ones. Safe to call concurrently."""
        async with self._lock:
            status = self.status = IndexStatus(state="indexing")
            try:
                on_disk = self.scan()
                indexed = self._store.signatures()
                for name in indexed.keys() - on_disk.keys():
                    self._store.remove_file(name)
                changed = [
                    name for name, path in on_disk.items() if indexed.get(name) != signature(path)
                ]
                status.pending = len(changed)
                for name in changed:
                    status.current = name
                    try:
                        await self._index_file(name, on_disk[name])
                    except Exception as exc:  # one bad file must not stop the others
                        log.warning("Failed to index %s: %s", name, exc)
                        status.failures[name] = str(exc)
                    status.processed += 1
                status.state = "idle"
            except Exception as exc:
                log.exception("Indexing failed")
                status.state = "error"
                status.error = str(exc)
            finally:
                status.current = None
                status.files = len(self._store.signatures())
                status.chunks = self._store.count()
            return status

    async def _index_file(self, name: str, path: Path) -> None:
        chunks = [
            Chunk(path=name, text=text, page=section.page, heading=section.heading)
            for section in await asyncio.to_thread(read_sections, path)
            for text in chunk_text(section.text, self._chunk_size, self._chunk_overlap)
        ]
        # Embed the heading too: it often names the topic the body never repeats.
        inputs = [f"{c.heading}\n{c.text}" if c.heading else c.text for c in chunks]
        vectors = await self._embedder.embed(inputs) if chunks else []
        self._store.replace_file(name, signature(path), chunks, vectors)
