"""Thin async client for a local Ollama server."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

import httpx


class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class ChatModel(Protocol):
    def stream_chat(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]: ...


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    """Implements both :class:`Embedder` and :class:`ChatModel` against Ollama's HTTP API."""

    def __init__(
        self,
        base_url: str,
        chat_model: str,
        embed_model: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        embed_batch_size: int = 32,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=httpx.Timeout(10.0, read=300.0), transport=transport
        )
        self.chat_model = chat_model
        self.embed_model = embed_model
        self._batch = embed_batch_size

    async def aclose(self) -> None:
        await self._client.aclose()

    async def installed_models(self) -> set[str]:
        data = await self._request("GET", "/api/tags")
        return {model["name"] for model in data.get("models", [])}

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch):
            batch = list(texts[start : start + self._batch])
            data = await self._request(
                "POST", "/api/embed", json={"model": self.embed_model, "input": batch}
            )
            vectors.extend(data["embeddings"])
        return vectors

    async def stream_chat(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        payload = {"model": self.chat_model, "messages": list(messages), "stream": True}
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code != 200:
                    await response.aread()
                    raise OllamaError(_describe(response))
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if "error" in event:
                        raise OllamaError(event["error"])
                    token = event.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if event.get("done"):
                        return
        except httpx.TransportError as exc:
            raise OllamaError(f"Cannot reach Ollama at {self._client.base_url}: {exc}") from exc

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            raise OllamaError(f"Cannot reach Ollama at {self._client.base_url}: {exc}") from exc
        if response.status_code != 200:
            raise OllamaError(_describe(response))
        return response.json()


def _describe(response: httpx.Response) -> str:
    try:
        detail = response.json().get("error", response.text)
    except ValueError:
        detail = response.text
    return f"Ollama returned {response.status_code}: {detail}"
