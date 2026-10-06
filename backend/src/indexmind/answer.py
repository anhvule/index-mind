"""Turning retrieved chunks into a cited, streamed answer."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from indexmind.llm import ChatModel
from indexmind.retrieval import Hit

NOT_FOUND = "I couldn't find anything about that in your documents."

SYSTEM_PROMPT = f"""You answer questions using only the numbered sources provided.

Rules:
- Use only facts stated in the sources. Do not use outside knowledge.
- After each sentence that uses a source, cite it with its number in square brackets, e.g. [2].
- If the sources do not contain the answer, reply exactly: "{NOT_FOUND}"
- Be concise. Prefer short paragraphs or bullet points.
"""

_CITATION = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class Source:
    id: int
    path: str
    page: int | None
    heading: str | None
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "page": self.page,
            "heading": self.heading,
            "excerpt": self.excerpt,
        }


def to_sources(hits: Sequence[Hit]) -> list[Source]:
    return [
        Source(
            id=n,
            path=hit.chunk.path,
            page=hit.chunk.page,
            heading=hit.chunk.heading,
            excerpt=hit.chunk.text,
        )
        for n, hit in enumerate(hits, start=1)
    ]


def build_messages(
    question: str, sources: Sequence[Source], history: Sequence[dict[str, str]] = ()
) -> list[dict[str, str]]:
    blocks = []
    for source in sources:
        label = source.path
        if source.page is not None:
            label += f", page {source.page}"
        if source.heading:
            label += f", section {source.heading}"
        blocks.append(f"[{source.id}] ({label})\n{source.excerpt}")
    context = "\n\n".join(blocks)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": f"Sources:\n\n{context}\n\nQuestion: {question}"},
    ]


def cited_ids(answer: str, sources: Sequence[Source]) -> list[int]:
    valid = {source.id for source in sources}
    seen: list[int] = []
    for match in _CITATION.finditer(answer):
        number = int(match.group(1))
        if number in valid and number not in seen:
            seen.append(number)
    return seen


class Answerer:
    def __init__(self, chat: ChatModel, min_similarity: float) -> None:
        self._chat = chat
        self._min_similarity = min_similarity

    async def stream(
        self, question: str, hits: Sequence[Hit], history: Sequence[dict[str, str]] = ()
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Yield (event, payload) pairs: one ``sources``, many ``token``, one ``done``."""
        relevant = [hit for hit in hits if hit.similarity >= self._min_similarity]
        if not relevant:
            # Nothing close enough: answering anyway would invite a hallucination.
            yield "sources", {"sources": []}
            yield "token", {"text": NOT_FOUND}
            yield "done", {"cited": [], "abstained": True}
            return

        sources = to_sources(relevant)
        yield "sources", {"sources": [source.to_dict() for source in sources]}
        parts: list[str] = []
        async for token in self._chat.stream_chat(build_messages(question, sources, history)):
            parts.append(token)
            yield "token", {"text": token}
        answer = "".join(parts)
        cited = cited_ids(answer, sources)
        abstained = NOT_FOUND.rstrip(".") in answer and not cited
        yield "done", {"cited": cited, "abstained": abstained}
