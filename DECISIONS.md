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


## 8. Title starts as nullable

**Status:** Accepted (2026-10-05)

**Context.** The first message in a conversation is the most important one and the LLM is the one that generates the title, so it should not be required at creation time. It will be updated later when the first message is received.

**Decision.** Use nullable title for conversations.

**Consequences.**
-We have to handle a null title when listing conversations, and if no title is generated after the first message we can use the id as a fallback.
-When we need to display the conversation title, we first try to get it from the conversation object, if it's null, we generate it using the first message and update the conversation object. 
-The title generation may fail, so we need to handle that case with a retry logic.
-The title generation is a new request that needs to be made using the first message, so we need to make sure we have the first message before generating the title.
-The title generation only needs to be made in the first message to no override the user manually updated titles.
-We need to handle the case where the user manually updates the title after the title generation, in this case we should use the user updated title.


## 9. use role as a simple string

**Status:** Accepted (2026-10-06)

**Context.** We have three roles: user, system and assistant. It's not necessary to have a dedicated enum for this.

**Decision.** Use simple strings for the role column in the messages table.

**consequences**
- will need a pydantic Literal  for the role column in the API
- will need to handle the case where the role is not one of the expected values in the API


## 10. use server_default=func.clock_timestamp() instead of server_default=func.now() for the message created_at

**Status:** Accepted (2026-10-06)

**Context.** The server_default=func.now() return the time when the transaction was started, not when the message was created. We need to use the time when the message was created.

**Decision.** Use server_default=func.clock_timestamp() for the message created_at column.

**Consequences.**
- the messages created_at will be more accurate


## 11. Message role has to be constraint to ['user', 'system', 'assistant', 'tool']

**Status:** Accepted (2026-10-11)

**Context.** The message role is used to identify the role of the message sender and it should be one of the following values: 'user', 'system', 'assistant', 'tool'.

**Decision.** Use a CheckConstraint to constraint the message role to ['user', 'system', 'assistant', 'tool'].

**Consequences.**
- the messages role will be more accurate
- 'banana', 'apple' will not be accepted as a role