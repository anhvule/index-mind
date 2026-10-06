from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from indexmind import __version__


def create_app() -> FastAPI:
    app = FastAPI(title="IndexMind", version=__version__)
    # The Electron renderer is served from file:// or the Vite dev server.
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
