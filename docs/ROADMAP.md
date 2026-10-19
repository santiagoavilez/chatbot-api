# Roadmap

Step-by-step build plan for a simple ChatGPT/Claude-style chat API. Work through the phases in order: each one depends on the previous one. Tick the boxes as you go and update **Current phase**.

**Current phase: 4 OpenRouter client**

| Phase | Goal                                                    | Status |
| -------| ---------------------------------------------------------| --------|
| 0     | Foundation (scaffolding, Docker, config, docs)          | Done   |
| 1     | Verify the database starts and connects                 | Done   |
| 2     | Models (SQLAlchemy + Alembic) and schemas (Pydantic v2) | Done   |
| 3     | Repository layer                                        | Done   |
| 4     | OpenRouter client                                       | Next   |
| 5     | Conversations CRUD                                      | Todo   |
| 6     | Chat endpoint (the core)                                | Todo   |
| 7     | Error handling                                          | Todo   |
| 8     | Tests                                                   | Todo   |
| 9     | Streaming (SSE)                                         | Todo   |
| 10    | Hardening (auth, rate limiting, CI)                     | Todo   |
| V2    | RAG                                                     | Later  |

## Rules that apply to every phase

- Everything that touches I/O is `async`. Never call a blocking library (`requests`, sync DB drivers, `time.sleep`) inside an `async def`: it blocks the event loop and stalls every other request.
- Routers stay thin: validate, call a service, return. Business logic lives in services; SQL lives in repositories.
- Test a piece in isolation (script or test) before wiring it into an endpoint.
- One phase = a few small commits, with tests and docs alongside the behavior.
- Add a configuration variable only when code uses it. Document it in [CONFIGURATION.md](CONFIGURATION.md).

---

## Phase 0: Foundation (done)

- [x] FastAPI app with `/` and `/health`
- [x] Docker Compose: API (hot reload) + PostgreSQL with pgvector
- [x] Settings with `pydantic-settings`
- [x] Docs: README, DECISIONS, ARCHITECTURE, CONFIGURATION

---

## Phase 1: Verify the database (done)

Prove the stack works end to end before modeling anything.

- [x] Align the DB password between `POSTGRES_PASSWORD` and `DATABASE_URL` in `.env`
- [x] Align the `DATABASE_URL` driver: use `postgresql+asyncpg://` (required by async SQLAlchemy); update the default in `config.py` too
- [x] `docker compose down -v && docker compose up --build`, then confirm `/health` and `/docs`
- [x] Create `app/db/session.py` with an async engine and a session factory
- [x] Run a trivial `SELECT 1` through the async session (loose script or temporary endpoint)
- [x] Enable the `vector` extension later in a migration, not by hand
  
**Done when:** a script opens an async session against the Compose DB and `SELECT 1` returns.

**Gotcha:** the Postgres volume keeps the password from the first start. Changing it requires `down -v`.

---

## Phase 2: Models and schemas (done)

Two different model families. Do not mix them.

- **SQLAlchemy models** describe tables.
- **Pydantic v2 schemas** describe what enters and leaves the API.

### Tables

- [x] `Conversation`: `id` (UUID), `title`, `created_at`, `updated_at`
- [x] `Message`: `id` (UUID), `conversation_id` (FK, `ON DELETE CASCADE`), `role` (`system` | `user` | `assistant`), `content`, `created_at`
- [x] Index on `messages(conversation_id, created_at)`
- [x] Relationship `Conversation.messages` ordered by `created_at`
- [x] Alembic initialized and configured for the async engine
- [x] First migration generated, **read by you**, and applied

### Schemas (Pydantic v2) (done)

- [x] `ConversationCreate`, `ConversationRead`, `ConversationUpdate`
- [x] `MessageCreate`, `MessageRead`
- [x] `ChatRequest` (user content, optional model), `ChatResponse`
- [x] `role` as a `Literal` or `Enum`, not a free string
- [x] Field constraints (`min_length`, `max_length`) on user input
- [x] Read schemas use `model_config = ConfigDict(from_attributes=True)` so they accept ORM objects

**Done when:** you can create and read rows from a script, and the migration applies cleanly on an empty database.

**Gotchas:**
- In Pydantic v2 use `model_validate`, `model_dump` and `ConfigDict`; the v1 names (`from_orm`, `.dict()`, `class Config`) are deprecated.
- Async SQLAlchemy does not lazy-load relationships. Load them explicitly (`selectinload`) or you will hit `MissingGreenlet`.

---

## Phase 3: Repository layer (done)

All SQL lives here. Services never write queries.

- [x] `ConversationRepository`: `create`, `get`, `list` (paginated), `update_title`, `delete`
- [x] `MessageRepository`: `add`, `list_by_conversation` (ordered, optionally last N)
- [x] Repositories receive an `AsyncSession`; they do not create sessions or commit on their own
- [x] FastAPI dependency `get_db` that yields a session per request
- [x] Define the transaction boundary (two commit per request, in the service or dependency)
 **Every chat request has two commits:** one before sending the prompt to the LLM and one before returning the response to the client.
- [x] Return `None` (or raise a domain error) for missing rows; do not return HTTP errors from here

**Done when:** each method is exercised against a real test database.

---

## Phase 4: OpenRouter client (next)

Separate module. Prove it with a loose script before any endpoint uses it.

- [ ] Move `httpx` from dev to main dependencies: `uv add httpx`
- [ ] Module `app/clients/openrouter.py`
- [ ] One reused `httpx.AsyncClient` (created at app startup via `lifespan`, closed at shutdown). Never create a client per request.
- [ ] Base URL, `Authorization: Bearer <key>` header, and default timeouts set on the client
- [ ] Explicit timeouts (connect, read, total). The default is not enough for LLM calls.
- [ ] Method `chat(messages, model) -> str` for non-streaming
- [ ] Map provider failures to domain exceptions (timeout, 429, 5xx, invalid response)
- [ ] Loose script: send a real prompt and print the answer
- [ ] Define a small interface (Protocol) so services can be tested with a fake client

**Done when:** the script returns a real model answer, and a wrong key or a tiny timeout raises your domain exceptions rather than raw httpx errors.

**Gotchas:**
- `requests` inside `async def` blocks the event loop. Use `httpx.AsyncClient`.
- Do not log the API key or full request headers.
- Pick a default model via a setting (a free or cheap model for development).

---

## Phase 5: Conversations CRUD

Plain HTTP and database work, no LLM involved.

- [ ] `POST /conversations`
- [ ] `GET /conversations` (pagination: `limit`, `offset`)
- [ ] `GET /conversations/{id}` (includes messages)
- [ ] `PATCH /conversations/{id}` (rename)
- [ ] `DELETE /conversations/{id}` (cascade deletes messages)
- [ ] `response_model` set on every route; correct status codes (201, 204, 404)
- [ ] Routers in `app/api/`, registered in `main.py` with a prefix and tags

**Done when:** you can drive the full lifecycle from `/docs` or Bruno, and a missing id returns a clean 404.

---

## Phase 6: Chat endpoint (the core)

This is where everything comes together and what a reviewer looks at first.

`POST /conversations/{id}/messages`

Flow, in one service method:

1. [ ] Load the conversation (404 if it does not exist)
2. [ ] Save the user message
3. [ ] Build the history from stored messages (ordered; add an optional system prompt)
4. [ ] Call the model through the OpenRouter client
5. [ ] Save the assistant message
6. [ ] Return the assistant message

Decisions to make and write down in [DECISIONS.md](../DECISIONS.md):

- [ ] What happens if the model call fails after the user message was saved? (keep it and let the user retry, or roll back)
- [ ] Transaction scope: do not hold a DB transaction open during a slow network call if you can avoid it
- [ ] History limits: cap by message count or approximate tokens so long conversations do not exceed the model context
- [ ] Auto-title the conversation from the first message (optional)

**Done when:** a conversation can go back and forth with a real model and the history survives a restart.

---

## Phase 7: Error handling

Make failures predictable. The client should always receive a consistent error body.

- [ ] Domain exceptions: `ConversationNotFound`, `ProviderTimeout`, `ProviderRateLimited`, `ProviderUnavailable`, `InvalidProviderResponse`
- [ ] Exception handlers registered on the app, mapping to HTTP statuses:

| Situation | Status |
|---|---|
| Conversation does not exist | 404 |
| Invalid input | 422 (FastAPI default) |
| Provider timeout | 504 |
| Provider rate limit (429) | 429 with `Retry-After` when available |
| Provider down or 5xx | 502 |
| Unexpected error | 500 with a generic message |

- [ ] One error response shape (for example `{"error": {"code": "...", "message": "..."}}`)
- [ ] Never leak stack traces, SQL or provider keys to the client
- [ ] Structured logging with a request id
- [ ] Limited retry with backoff for transient provider errors (not for 4xx)

**Done when:** every failure above is reproducible in a test and returns the documented status and body.

---

## Phase 8: Tests

Start earlier than this phase; consolidate here.

- [ ] `pytest` + `pytest-asyncio` configured (async mode in `pyproject.toml`)
- [ ] Test client: `httpx.AsyncClient` with `ASGITransport`
- [ ] Separate test database, created and cleaned per run or per test
- [ ] Override the DB session and the OpenRouter client with `app.dependency_overrides`
- [ ] **Never call the real provider in tests.** Use a fake client.
- [ ] Repository tests (real DB)
- [ ] Service tests (fake OpenRouter client): history building, save order, failure paths
- [ ] API tests: CRUD, chat happy path, every error case from Phase 7
- [ ] Coverage report; focus on the chat service and error paths

**Done when:** `uv run pytest` passes on a clean checkout and in CI.

---

## Phase 9: Streaming (SSE)

- [ ] Client method that streams tokens from OpenRouter (`stream: true`) as an async generator
- [ ] Endpoint returning `StreamingResponse` with `text/event-stream`
- [ ] SSE format: `data: ...\n\n`, with a final event marking completion
- [ ] Accumulate the full answer while streaming and save the assistant message when it ends
- [ ] Handle client disconnects (cancel the upstream request; decide what to persist)
- [ ] Error during a stream: send an error event, since the HTTP status was already sent
- [ ] Verify there is no proxy buffering (headers such as `Cache-Control: no-cache`)
- [ ] Tests for the stream (fake generator)

**Done when:** `curl -N` shows tokens arriving incrementally and the final message is stored once.

**Gotcha:** the DB session created by a request dependency may be closed before a long stream finishes. Be deliberate about which session saves the final message.

---

## Phase 10: Hardening

- [ ] JWT authentication and per-user conversation ownership (add `JWT_SECRET` as a required setting)
- [ ] CORS for the frontend origin (add `CORS_ORIGINS` when a frontend exists)
- [ ] Rate limiting per user or IP
- [ ] Health check that verifies the database (readiness)
- [ ] Production Docker stage (no bind mount, no `--reload`)
- [ ] CI: lint, type check, tests on every push
- [ ] Update README, ARCHITECTURE and DECISIONS to match reality

---

## V2: RAG

Only after V1 is stable. See [ARCHITECTURE.md](ARCHITECTURE.md#v2-rag).

- [ ] Migration enabling the `vector` extension
- [ ] Document upload and chunking
- [ ] Embeddings via OpenRouter or another provider
- [ ] Vector table and similarity search with pgvector
- [ ] Retrieval step inserted into the chat service before the model call
- [ ] Per-user document isolation
- [ ] Evaluation: does retrieval improve answers on a small test set?

---

## Suggested folder structure by the end of Phase 7

```
app/
├── main.py             # app, lifespan, router and handler registration
├── config.py
├── api/                # routers
├── schemas/            # Pydantic v2 models
├── services/           # chat and conversation logic
├── repositories/       # SQL
├── db/                 # engine, session, ORM models
├── clients/            # OpenRouter client
└── core/               # exceptions, error handlers, logging
tests/
alembic/
```
