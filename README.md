# IndexMind

Ask questions about your own documents — privately, on your own machine.

IndexMind is a desktop app that indexes a folder of PDFs, Markdown and text
files and answers questions about them with a local LLM served by
[Ollama](https://ollama.com). Every answer cites the passages it came from, and
when your documents don't cover a question it says so instead of guessing.
Nothing leaves your computer.

## Features

- **Local only** — models run in Ollama; the index is a SQLite file.
- **Cited answers** — click a citation to see the exact passage.
- **Hybrid search** — vector similarity plus BM25 keyword matching, merged with
  reciprocal rank fusion, so exact names and codes are found too.
- **Incremental indexing** — only new or changed files are re-embedded.
- **Honest abstention** — weak matches skip the model entirely.

## How it works

```
┌──────────── Electron ────────────┐        ┌──────── Python (FastAPI) ────────┐
│ React UI ──fetch / SSE──────────────────▶ │ /ask  → retrieve → prompt → LLM  │
│ main process: spawns backend     │        │ /index/status, /index/rescan     │
└──────────────────────────────────┘        │ SQLite store · BM25 · numpy      │
                                            └───────────────┬──────────────────┘
                                                            ▼
                                                 Ollama (chat + embeddings)
```

1. **Index.** Files are split into sections (PDF pages, Markdown headings),
   chunked with overlap, embedded and stored in SQLite.
2. **Retrieve.** A question is matched by embedding similarity and BM25; the
   two rankings are fused.
3. **Answer.** The top passages are numbered and the model is told to answer
   only from them, citing `[n]`. The answer streams to the UI over server-sent
   events.

## Getting started

Prerequisites: [Ollama](https://ollama.com/download), [uv](https://docs.astral.sh/uv/),
Node.js 22+ and pnpm.

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

```bash
cd frontend
pnpm install
pnpm dev
```

The app starts the backend for you. Put documents in the repo's `documents/`
folder (the **Open folder** button takes you there) and press **Rescan**. Its
contents are git-ignored. An installed build uses `~/Documents/IndexMind`
instead, and `INDEXMIND_DOCS_DIR` overrides either.

### Running the backend on its own

```bash
cd backend
uv run indexmind --port 8765
curl -N localhost:8765/ask -H 'content-type: application/json' -d '{"question":"..."}'
```

Settings are read from `INDEXMIND_*` environment variables or `backend/.env`;
see [`backend/.env.example`](backend/.env.example).

## Development

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && pnpm typecheck && pnpm test
```

## Roadmap

- Packaged installers with a bundled Python runtime
- Reranking retrieved passages with a cross-encoder
- More formats (DOCX, HTML)

## License

[MIT](LICENSE) © Le Anh Vu
