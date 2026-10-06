"""A small Okapi BM25 index for exact-term matching alongside vector search."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

_TOKEN = re.compile(r"\w+", re.UNICODE)

# Kept deliberately short: only words that carry no meaning in a question.
STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
        "from", "how", "i", "in", "is", "it", "my", "of", "on", "or", "the", "this",
        "to", "was", "what", "when", "where", "which", "who", "why", "will", "with",
        "you", "your",
    }
)  # fmt: skip


def tokenize(text: str) -> list[str]:
    """Lower-case, strip accents ("Café" -> "cafe") and drop stopwords."""
    folded = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return [token for token in _TOKEN.findall(folded) if token not in STOPWORDS]


class BM25Index:
    def __init__(self, documents: Sequence[str], k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._term_freqs = [Counter(tokenize(doc)) for doc in documents]
        self._lengths = [sum(tf.values()) for tf in self._term_freqs]
        self._avg_length = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0
        doc_freq: Counter[str] = Counter()
        for tf in self._term_freqs:
            doc_freq.update(tf.keys())
        n = len(documents)
        self._idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5)) for term, df in doc_freq.items()
        }

    def __len__(self) -> int:
        return len(self._term_freqs)

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        """Return up to ``k`` (document index, score) pairs with a positive score."""
        terms = [t for t in set(tokenize(query)) if t in self._idf]
        if not terms:
            return []
        scores = []
        for index, tf in enumerate(self._term_freqs):
            score = sum(self._term_score(tf, self._lengths[index], term) for term in terms)
            if score > 0:
                scores.append((index, score))
        scores.sort(key=lambda pair: pair[1], reverse=True)
        return scores[:k]

    def _term_score(self, tf: Counter[str], length: int, term: str) -> float:
        freq = tf.get(term, 0)
        if not freq:
            return 0.0
        norm = 1 - self._b + self._b * length / (self._avg_length or 1)
        return self._idf[term] * freq * (self._k1 + 1) / (freq + self._k1 * norm)
