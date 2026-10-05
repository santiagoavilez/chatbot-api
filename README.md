# Chatbot API

A chat completion API in the style of ChatGPT and Claude, built with FastAPI and PostgreSQL. Model access goes through [OpenRouter](https://openrouter.ai). Retrieval-Augmented Generation (RAG) is planned for V2.

> **Status: V1 boilerplate.** The project scaffolding, containerized environment and configuration layer are in place. Only `GET /` and `GET /health` exist today. See [Roadmap](#roadmap).

## What works today

- FastAPI application with auto-generated OpenAPI docs (`/docs`)
- Health check endpoint (`/health`)
- Typed, validated configuration loaded from environment variables (`pydantic-settings`)
- Reproducible dev environment with Docker Compose (API with hot reload + PostgreSQL with pgvector)
- Dependency management with `uv` and a committed lockfile

## What is planned

- Chat completion endpoint backed by OpenRouter (V1)
- Conversation and message persistence (V1)
- Authentication with JWT (V1)
- RAG over user documents using pgvector (V2)

## Quick start

**Prerequisites:** Docker with Docker Compose v2.

1. Create your environment file:

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell: `Copy-Item .env.example .env`

2. Edit `.env` and set at least the required variables. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full reference.

   Set `API_HOST=0.0.0.0`. Inside a container, `localhost` is not reachable from the host machine.

3. Start the stack:

   ```bash
   docker compose up
   ```

4. Verify:

   - Health check: <http://localhost:8000/health> returns `{"status": "ok"}`
   - Interactive API docs: <http://localhost:8000/docs>

   Replace `8000` with your `API_PORT` if you changed it.

The API runs with hot reload: edits under `app/` are picked up automatically. Rebuild the image when dependencies change:

```bash
docker compose up --build
```

## Common commands

| Task | Command |
|---|---|
| Start in background | `docker compose up -d` |
| Follow API logs | `docker compose logs -f api` |
| Stop | `docker compose down` |
| Restart | `docker compose restart` |
| Rebuild images | `docker compose build` |
| **Reset the database (destroys all data)** | `docker compose down -v && docker compose up -d` |

## Local development without Docker

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/). You also need a reachable PostgreSQL instance and a matching `DATABASE_URL`.

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Run tests:

```bash
uv run pytest
```

## Project layout

```
.
├── app/
│   ├── main.py          # FastAPI app and routes
│   └── config.py        # Settings loaded from the environment
├── bruno-collection/    # Bruno API client collection for manual testing
├── docs/
│   ├── ARCHITECTURE.md  # System design and V2 direction
│   └── CONFIGURATION.md # Environment variable reference
├── DECISIONS.md         # Architecture decision records
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml       # Dependencies (managed with uv)
```

## Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Web framework | FastAPI + Uvicorn |
| Database | PostgreSQL 17 with pgvector |
| DB access | SQLAlchemy (async) + asyncpg, migrations with Alembic |
| LLM gateway | OpenRouter |
| Configuration | pydantic-settings |
| Packaging | uv |
| Environment | Docker Compose |
| Tests | pytest, pytest-asyncio, httpx |

The reasoning behind each choice is recorded in [DECISIONS.md](DECISIONS.md).

> SQLAlchemy, asyncpg and Alembic are declared as dependencies but are not wired into the app yet.

## Roadmap

| Version | Scope |
|---|---|
| **V1** | Chat completions via OpenRouter, conversation persistence, JWT authentication, tests |
| **V2** | RAG: document ingestion, embeddings, vector retrieval with pgvector, context injection |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how V2 is expected to fit into the current design.
