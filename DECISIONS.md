# Decisions

Architecture decision records for this project. Each entry states the context, the decision, the alternatives considered and the consequences accepted.

Status values: **Accepted**, **Superseded**, **Deferred**.

## 1. PostgreSQL with pgvector instead of MongoDB

**Status:** Accepted (2026-10-01)

**Context.** The system stores relational data (users, conversations, messages) and, from V2, vector embeddings for RAG.

**Decision.** Use PostgreSQL with the pgvector extension.

**Alternatives considered.**
- MongoDB: flexible documents, but vector search and relational integrity would need extra work or a second system.
- A dedicated vector database (Pinecone, Qdrant, etc.): strong at similarity search, but adds another service and a consistency problem between two stores.

**Consequences.**
- One database for relational and vector data.
- Strong constraints and transactions for conversation data.
- Vector search scale is bounded by what Postgres + pgvector can handle. Revisit if embeddings grow to a very large size.
- Schema changes require migrations (Alembic).

## 2. FastAPI as the web framework

**Status:** Accepted

**Context.** An async API that calls an external LLM and a database, with typed contracts and generated documentation.

**Decision.** Use FastAPI.

**Alternatives considered.**
- Django: batteries included (ORM, admin, auth), but heavier, and async support is less central to its design.
- Flask: minimal, but validation, typing and OpenAPI would be assembled by hand.

**Consequences.**
- Request/response validation with Pydantic and automatic OpenAPI docs at `/docs`.
- Async-first, which fits network-bound LLM calls.
- No built-in ORM, admin or auth: these are assembled explicitly (SQLAlchemy, Alembic, JWT).

## 3. uv for dependency management

**Status:** Accepted

**Context.** Reproducible installs locally and in Docker, with a pinned Python version.

**Decision.** Use `uv` with `pyproject.toml` and a committed `uv.lock`.

**Alternatives considered.** pip with `requirements.txt` (no lockfile or resolver guarantees by default), Poetry (mature, slower).

**Consequences.**
- Fast, deterministic installs (`uv sync --frozen` in the Dockerfile).
- Python version tracked in `.python-version` and `requires-python`.
- Contributors need `uv` installed for non-Docker workflows.

## 4. Docker and Docker Compose for the environment

**Status:** Accepted

**Context.** The application and its database must run identically on any machine.

**Decision.** Containerize the API and run it with PostgreSQL through Docker Compose.

**Alternatives considered.** Running Python and Postgres natively (works until machines differ).

**Consequences.**
- One command (`docker compose up`) starts the full stack.
- Hot reload through a bind mount; polling is enabled so it works on Windows.
- The current setup targets development. Production needs a separate image and secret management.

## 5. OpenRouter as the LLM gateway

**Status:** Accepted

**Context.** The product should be able to switch or compare models without code changes.

**Decision.** Call models through OpenRouter.

**Alternatives considered.** Calling OpenAI or Anthropic directly: simpler per provider, but each requires its own client, key and request format.

**Consequences.**
- One API and one key for many models.
- Pay-per-use pricing; some models offer limited free tiers, which are not a basis for production.
- An extra network hop and a dependency on a third party. The client is kept behind a service boundary so it can be replaced.

## 6. Configuration through pydantic-settings

**Status:** Accepted

**Context.** Configuration must be typed, validated and fail fast.

**Decision.** Declare all settings in `app/config.py`. Required values have no default; secrets use `SecretStr`.

**Consequences.**
- A missing required variable stops the app at startup.
- Variables are added when code uses them, so documentation stays truthful.

## 7. JWT authentication and CORS

**Status:** Deferred

**Context.** Authentication and browser access are required before exposing the API, but neither is implemented.

**Decision.** Do not declare `JWT_SECRET`, `JWT_EXPIRATION_TIME` or `CORS_ORIGINS` until the features are built. They are listed as planned in [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

**Consequences.**
- No unused configuration implying features that do not exist.
- Must be revisited as part of V1 authentication work; `JWT_SECRET` should be required with no default.
