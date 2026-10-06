from indexmind.answer import NOT_FOUND, Answerer, build_messages, cited_ids, to_sources
from indexmind.retrieval import Hit
from indexmind.store import Chunk


class ScriptedChat:
    def __init__(self, *tokens: str) -> None:
        self.tokens = tokens
        self.messages = None

    async def stream_chat(self, messages):
        self.messages = messages
        for token in self.tokens:
            yield token


def hit(text: str, similarity: float, **kwargs) -> Hit:
    return Hit(Chunk("doc.md", text, **kwargs), similarity=similarity, score=0.0)


async def collect(stream):
    return [event async for event in stream]


async def test_low_similarity_abstains_without_calling_the_model():
    chat = ScriptedChat("should not run")
    answerer = Answerer(chat, min_similarity=0.5)

    events = await collect(answerer.stream("q", [hit("unrelated", 0.1)]))

    assert events[1] == ("token", {"text": NOT_FOUND})
    assert events[-1] == ("done", {"cited": [], "abstained": True})
    assert chat.messages is None


async def test_streams_tokens_and_reports_citations():
    chat = ScriptedChat("It is 25 days ", "[1].")
    answerer = Answerer(chat, min_similarity=0.2)

    events = await collect(answerer.stream("leave?", [hit("25 days of leave", 0.8)]))

    assert events[0][0] == "sources"
    assert [data["text"] for name, data in events if name == "token"] == ["It is 25 days ", "[1]."]
    assert events[-1] == ("done", {"cited": [1], "abstained": False})


def test_prompt_numbers_sources_with_location():
    sources = to_sources([hit("body", 0.9, page=4, heading="Intro")])

    messages = build_messages("why?", sources, history=[{"role": "user", "content": "hi"}])

    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "hi"}
    assert "[1] (doc.md, page 4, section Intro)\nbody" in messages[-1]["content"]


def test_cited_ids_ignores_unknown_and_duplicate_numbers():
    sources = to_sources([hit("a", 1.0), hit("b", 1.0)])

    assert cited_ids("x [2] y [9] z [2] [1]", sources) == [2, 1]
