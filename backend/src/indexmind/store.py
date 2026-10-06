"""Persistent chunk storage: SQLite for records, an in-memory numpy matrix for vector search."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    signature TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
    page INTEGER,
    heading TEXT,
    text TEXT NOT NULL,
    embedding BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
"""


@dataclass(frozen=True)
class Chunk:
    path: str
    text: str
    page: int | None = None
    heading: str | None = None
    id: int | None = None

    @property
    def location(self) -> str:
        parts = [self.path]
        if self.page is not None:
            parts.append(f"p. {self.page}")
        if self.heading:
            parts.append(self.heading)
        return " · ".join(parts)


class ChunkStore:
    """Stores chunks with their embeddings and answers nearest-neighbour queries.

    Vectors are L2-normalised on write so cosine similarity is a dot product.
    The matrix is rebuilt lazily after writes; a personal document folder fits
    comfortably in memory.
    """

    def __init__(self, db_path: Path | str) -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)
        self._lock = threading.Lock()
        self._cache: tuple[list[Chunk], np.ndarray] | None = None

    def signatures(self) -> dict[str, str]:
        return dict(self._db.execute("SELECT path, signature FROM files"))

    def replace_file(
        self, path: str, signature: str, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("every chunk needs exactly one vector")
        rows = [
            (path, c.page, c.heading, c.text, _normalise(v).tobytes())
            for c, v in zip(chunks, vectors, strict=True)
        ]
        with self._lock, self._db:
            self._db.execute("DELETE FROM files WHERE path = ?", (path,))
            self._db.execute("INSERT INTO files VALUES (?, ?)", (path, signature))
            self._db.executemany(
                "INSERT INTO chunks (path, page, heading, text, embedding) VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            self._cache = None

    def remove_file(self, path: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM files WHERE path = ?", (path,))
            self._cache = None

    def all_chunks(self) -> list[Chunk]:
        return self._load()[0]

    def count(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def search(self, query_vector: Sequence[float], k: int) -> list[tuple[Chunk, float]]:
        chunks, matrix = self._load()
        if not chunks:
            return []
        scores = matrix @ _normalise(query_vector)
        k = min(k, len(chunks))
        best = np.argpartition(-scores, k - 1)[:k]
        best = best[np.argsort(-scores[best])]
        return [(chunks[i], float(scores[i])) for i in best]

    def _load(self) -> tuple[list[Chunk], np.ndarray]:
        with self._lock:
            if self._cache is None:
                rows = self._db.execute(
                    "SELECT id, path, page, heading, text, embedding FROM chunks ORDER BY id"
                ).fetchall()
                chunks = [
                    Chunk(id=r[0], path=r[1], page=r[2], heading=r[3], text=r[4]) for r in rows
                ]
                matrix = (
                    np.vstack([np.frombuffer(r[5], dtype=np.float32) for r in rows])
                    if rows
                    else np.empty((0, 0), dtype=np.float32)
                )
                self._cache = (chunks, matrix)
            return self._cache


def _normalise(vector: Sequence[float]) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(array)
    return array / norm if norm else array
