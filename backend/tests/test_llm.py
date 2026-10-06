import json

import httpx
import pytest

from indexmind.llm import OllamaClient, OllamaError


def make_client(handler) -> OllamaClient:
    return OllamaClient(
        "http://ollama.test",
        chat_model="chat",
        embed_model="embed",
        transport=httpx.MockTransport(handler),
        embed_batch_size=2,
    )


async def test_embed_batches_requests():
    batches = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        batches.append(body["input"])
        return httpx.Response(200, json={"embeddings": [[float(len(t))] for t in body["input"]]})

    client = make_client(handler)

    vectors = await client.embed(["a", "bb", "ccc"])

    assert batches == [["a", "bb"], ["ccc"]]
    assert vectors == [[1.0], [2.0], [3.0]]


async def test_stream_chat_yields_tokens_until_done():
    lines = [
        {"message": {"content": "Hel"}, "done": False},
        {"message": {"content": "lo"}, "done": False},
        {"message": {"content": ""}, "done": True},
    ]
    body = "\n".join(json.dumps(line) for line in lines)
    client = make_client(lambda request: httpx.Response(200, text=body))

    tokens = [token async for token in client.stream_chat([{"role": "user", "content": "hi"}])]

    assert tokens == ["Hel", "lo"]


async def test_missing_model_raises_readable_error():
    client = make_client(lambda r: httpx.Response(404, json={"error": "model 'chat' not found"}))

    with pytest.raises(OllamaError, match="not found"):
        [token async for token in client.stream_chat([])]


async def test_unreachable_server_raises_ollama_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(OllamaError, match="Cannot reach Ollama"):
        await make_client(handler).installed_models()
