import pytest

from indexmind.chunking import chunk_text


def test_short_text_is_a_single_chunk():
    assert chunk_text("One paragraph.", size=100, overlap=10) == ["One paragraph."]


def test_empty_text_has_no_chunks():
    assert chunk_text("  \n\n ", size=100, overlap=10) == []


def test_chunks_respect_size_limit():
    text = "\n\n".join(f"Paragraph number {i} has some words in it." for i in range(50))

    chunks = chunk_text(text, size=200, overlap=40)

    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_consecutive_chunks_overlap():
    text = "\n\n".join(f"Sentence {i} talks about topic {i}." for i in range(30))

    chunks = chunk_text(text, size=120, overlap=40)

    for previous, following in zip(chunks, chunks[1:], strict=False):
        last_words = previous.split()[-2:]
        assert " ".join(last_words) in following


def test_oversized_paragraph_is_split():
    chunks = chunk_text("word " * 500, size=100, overlap=0)

    assert all(len(c) <= 100 for c in chunks)


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("text", size=10, overlap=10)
