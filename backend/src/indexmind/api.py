from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from indexmind import __version__
from indexmind.indexer import Indexer
from indexmind.llm import ChatModel, Embedder, OllamaClient
from indexmind.retrieval import Retriever
from indexmind.settings import Settings, get_settings
from indexmind.store import ChunkStore


@dataclass
class Services:
    settings: Settings
    store: ChunkStore
    indexer: Indexer
    retriever: Retriever
    chat: ChatModel
    tasks: set[asyncio.Task] = field(default_factory=set)

    def start_sync(self) -> None:
        async def run() -> None:
            await self.indexer.sync()
            self.retriever.invalidate()

        # Report "indexing" immediately so a status poll right after a rescan
        # request cannot observe the stale idle state.
        self.indexer.status.state = "indexing"
        task = asyncio.create_task(run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


def build_services(
    settings: Settings, embedder: Embedder | None = None, chat: ChatModel | None = None
) -> Services:
    ollama = None
    if embedder is None or chat is None:
        ollama = OllamaClient(settings.ollama_url, settings.chat_model, settings.embed_model)
    embedder = embedder or ollama
    store = ChunkStore(settings.data_dir / "index.db")
    indexer = Indexer(
        settings.docs_dir.expanduser().resolve(),
        store,
        embedder,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return Services(
        settings=settings,
        store=store,
        indexer=indexer,
        retriever=Retriever(store, embedder),
        chat=chat or ollama,
    )


def create_app(
    settings: Settings | None = None,
    *,
    embedder: Embedder | None = None,
    chat: ChatModel | None = None,
    index_on_startup: bool = True,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        services = build_services(settings, embedder, chat)
        app.state.services = services
        if index_on_startup:
            services.start_sync()
        yield
        for task in services.tasks:
            task.cancel()
        if isinstance(services.chat, OllamaClient):
            await services.chat.aclose()

    app = FastAPI(title="IndexMind", version=__version__, lifespan=lifespan)
    # The Electron renderer is served from file:// or the Vite dev server.
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/index/status")
    def index_status(request: Request) -> dict:
        services: Services = request.app.state.services
        return {"docs_dir": str(services.indexer.docs_dir), **services.indexer.status.to_dict()}

    @app.post("/index/rescan", status_code=202)
    async def rescan(request: Request) -> dict:
        services: Services = request.app.state.services
        services.start_sync()
        return {"started": True}

    return app
