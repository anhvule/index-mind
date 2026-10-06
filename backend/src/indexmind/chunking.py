"""Splitting sections into overlapping chunks small enough to embed."""

from __future__ import annotations

import re
from collections.abc import Iterator

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"[ \t]+")


def normalize(text: str) -> str:
    lines = (_WHITESPACE.sub(" ", line).strip() for line in text.splitlines())
    return "\n".join(lines).strip()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Greedily pack paragraphs (falling back to sentences, then hard cuts) into chunks.

    Consecutive chunks share up to ``overlap`` trailing characters so that a fact
    straddling a boundary is still retrievable from at least one chunk.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = normalize(text)
    if not text:
        return []

    chunks: list[str] = []
    current = ""
    for piece in _pieces(text, size):
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= size:
            current = candidate
            continue
        chunks.append(current)
        tail = _tail(current, overlap)
        current = f"{tail} {piece}".strip() if len(tail) + len(piece) < size else piece
    if current:
        chunks.append(current)
    return chunks


def _pieces(text: str, size: int) -> Iterator[str]:
    for paragraph in _PARAGRAPH_BREAK.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= size:
            yield paragraph
            continue
        for sentence in _SENTENCE_END.split(paragraph):
            for start in range(0, len(sentence), size):
                yield sentence[start : start + size]


def _tail(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    tail = text[-overlap:]
    # Start the overlap on a word boundary rather than mid-word.
    space = tail.find(" ")
    return tail[space + 1 :] if 0 <= space < len(tail) - 1 else tail
