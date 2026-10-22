# Writing endpoints

A practical guide for building the conversation CRUD endpoints (Phase 5). The chat endpoint
(`POST /conversations/{conversation_id}/messages`) is the worked example: read its files first,
then write yours in the same shape.

## The layers

A request flows through these layers, top to bottom. Each one has one job.

```
router  ->  dependency  ->  service  ->  repository  ->  model
```

| Layer | Lives in | Belongs here | Does not belong here |
|---|---|---|---|
| Router | `app/api/<resource>.py` | Path, verb, status code, `response_model`, calling the service, returning the result | Business rules, SQL, commits, `try/except` for domain errors |
| Dependency | `app/api/deps.py` | Building collaborators (session, repositories, service, LLM client) and handing them to the router | Request logic |
| Service | `app/services/<name>.py` | The use case: ordering of steps, rules, transaction boundary (`commit`), raising domain exceptions | HTTP types (`HTTPException`, status codes), SQL |
| Repository | `app/repositories/<name>.py` | Queries and `add`/`flush`. Returns models or `None` | `commit`, HTTP, business rules |
| Model | `app/models/<name>.py` | Table definition, constraints, indexes | Behaviour that needs a session |

Two more pieces sit beside the flow:

- **Schemas** (`app/schemas/`) describe what enters and leaves the API. Input schemas and
  `response_model` schemas are different classes.
- **Exception handlers** (`app/api/errors.py`) translate domain exceptions
  (`app/core/exceptions.py`) into HTTP responses. This is the only place that knows both worlds.

## Checklist for a correct endpoint

- [ ] **Input schema is not the response schema.** The client sends `ChatRequest`; the API returns
      `MessageRead`. The client never sends server-owned fields (`id`, `role`, timestamps).
- [ ] **`response_model` is set** on every route, so only declared fields leave the API.
- [ ] **Status codes are deliberate:** `200` read/update, `201` create, `204` delete (no body),
      `404` missing resource, `422` invalid input (FastAPI produces it from the schema).
- [ ] **Dependencies use `Annotated`**: `ChatServiceDep = Annotated[ChatService, Depends(...)]`.
- [ ] **Path and query params are typed.** `conversation_id: uuid.UUID` gives a free `422` for a
      malformed id. Bound pagination:
      `limit: Annotated[int, Query(ge=1, le=100)] = 20`, `offset: Annotated[int, Query(ge=0)] = 0`.
- [ ] **No business logic in routers.** If the router has an `if` about the domain, move it to
      the service.
- [ ] **Services own the commit.** Repositories only `add`/`flush`. One service method = one use
      case = the transaction boundary.
- [ ] **Services raise domain exceptions, not `HTTPException`.** The domain must stay HTTP-free
      so it can be reused (CLI, jobs, tests).
- [ ] **Handlers map domain exceptions to HTTP** and answer with our own generic message. Never
      echo a provider or database message to the client.
- [ ] **Tests use `app.dependency_overrides`** with a fake service: no database, no network.
      Clear the overrides after each test.
- [ ] **Model changes come with a migration** that you have read before applying.

## Worked example: the chat endpoint

Follow one request through the real files.

1. **Router** - `app/api/messages.py`. `send_message` receives `conversation_id` (typed
   `uuid.UUID`), the body `ChatRequest` and a `ChatServiceDep`. It calls
   `service.send_message(...)` and returns the result as `MessageRead` with `status_code=201`.
   Nothing else.
2. **Dependencies** - `app/api/deps.py`. `get_chat_service` builds the repositories from the
   request's session (`get_db`) and the LLM client from the shared `httpx.AsyncClient` stored on
   `app.state` (`get_llm_client`). The service depends on the `LLMClient` Protocol
   (`app/clients/llm.py`), not on OpenRouter.
3. **Service** - `app/services/chat.py`. `ChatService.send_message` loads the conversation
   (raises `ConversationNotFoundError`), saves the user message and commits, calls the model,
   saves the assistant message and its metric and commits again. The first commit ends the
   transaction before the slow network call; if the model fails, the user message is already
   saved. See decisions 15 and 16 in [DECISIONS.md](../DECISIONS.md).
4. **Repositories** - `app/repositories/`. `MessageRepository.add`,
   `MessageRepository.list_by_conversation`, `ConversationRepository.touch` and
   `MessageMetricRepository.add` run SQL and `flush`. None of them commits.
5. **Models** - `app/models/message.py`, `app/models/message_metric.py`. The metric lives in its
   own 1:1 table keyed by `message_id`.
6. **Errors** - `app/api/errors.py`. `register_exception_handlers(app)` (called in
   `app/main.py`) maps each domain exception to a status and a fixed message, adds
   `Retry-After` for rate limits and logs the original detail server-side.
7. **Tests** - `tests/services/test_chat_service.py` uses fakes for the session, repositories and
   LLM client. `tests/api/test_messages.py` overrides `get_chat_service` with a fake service and
   calls the app through `httpx.ASGITransport`.

## Starting a new chat

`POST /conversations/messages` (no id) is the "new chat" entry point. It takes the same
`ChatRequest` body, creates a conversation, runs the first turn and returns `201` with the
assistant `MessageRead`; its `conversation_id` is the id of the new conversation.

- **Route:** `app/api/messages.py` (`start_conversation`). It has two path segments, so it never
  matches `/{conversation_id}/messages`.
- **Service:** `ChatService.start_conversation` creates the conversation and delegates to the
  same private `_run_turn` used by `send_message`, so the turn logic exists once.
- **Failures:** the conversation and user message are committed before the model call. If the
  provider fails, the domain exception carries `conversation_id` and `app/api/errors.py` adds it
  to the error body (`{"detail": "...", "conversation_id": "..."}`), so the client can retry on
  `POST /conversations/{conversation_id}/messages`. See decision 19 in
  [DECISIONS.md](../DECISIONS.md).

## Writing the conversation CRUD

Create `app/api/conversations.py` with its own `APIRouter(prefix="/conversations",
tags=["conversations"])`, register it in `app/main.py` next to the messages router, and add a
`ConversationService` (`app/services/conversation.py`) if the endpoint has any rule beyond
"call the repository". Suggested route table:

| Route | Success | Failure | Notes |
|---|---|---|---|
| `POST /conversations` | `201` + `ConversationRead` | `422` | Title is optional (decision 8) |
| `GET /conversations` | `200` + list | `422` for bad `limit`/`offset` | Paginated, uses `list_recent` |
| `GET /conversations/{id}` | `200` + conversation with messages | `404` | Load messages explicitly (`selectinload`) |
| `PATCH /conversations/{id}` | `200` + `ConversationRead` | `404`, `422` | Rename only |
| `DELETE /conversations/{id}` | `204`, empty body | `404` | Messages go with it (`ON DELETE CASCADE`) |

Illustrative fragments (shapes only, not a full solution):

```python
# Pagination parameter
limit: Annotated[int, Query(ge=1, le=100)] = 20

# Delete: the status code is declared on the route
@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)

# Service: a missing row becomes a domain exception, not an HTTP one
if conversation is None:
    raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
```

`ConversationNotFoundError` already maps to `404`, so a new route that raises it needs no new
handler. Write each route test-first with a fake service, then wire the real one.
