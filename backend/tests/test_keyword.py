from indexmind.keyword import BM25Index, tokenize


def test_tokenize_folds_case_accents_and_stopwords():
    assert tokenize("What is the Café's WiFi password?") == ["cafe", "s", "wifi", "password"]


def test_bm25_prefers_documents_with_rare_query_terms():
    index = BM25Index(
        [
            "the printer is on the second floor",
            "the wifi password is on the fridge",
            "lunch is served on the second floor",
        ]
    )

    results = index.search("wifi password", k=3)

    assert results[0][0] == 1
    assert len(results) == 1


def test_bm25_returns_nothing_for_unknown_terms():
    assert BM25Index(["alpha beta"]).search("gamma", k=5) == []


def test_bm25_handles_empty_corpus():
    assert BM25Index([]).search("anything", k=5) == []
