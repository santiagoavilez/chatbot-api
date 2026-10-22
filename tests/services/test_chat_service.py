import uuid
from collections.abc import Sequence
from types import SimpleNamespace

import pytest

from app.clients.llm import ChatMessage, ChatResult
from app.core.exceptions import ConversationNotFoundError, LLMServerError
from app.models import Message
from app.services.chat import ChatService

MODEL = "google/gemma-4-31b-it:free"


class FakeSession:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1
        self.events.append("commit")


class FakeConversationRepository:
    def __init__(self, conversation: object | None) -> None:
        self.conversation = conversation
        self.touched = 0

    async def get(self, conversation_id: uuid.UUID) -> object | None:
        return self.conversation

    async def touch(self, conversation: object) -> None:
        self.touched += 1


class FakeMessageRepository:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.stored: list[Message] = []
        self.last_limit: int | None = None

    async def add(
        self, content: str, conversation_id: uuid.UUID, role: str, model: str | None
    ) -> Message:
        message = Message(
            id=uuid.uuid4(),
            content=content,
            conversation_id=conversation_id,
            role=role,
            model=model,
        )
        self.stored.append(message)
        self.events.append(f"add:{role}")
        return message

    async def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int, offset: int
    ) -> Sequence[Message]:
        self.last_limit = limit
        return self.stored[-limit:]


class FakeMetricRepository:
    def __init__(self) -> None:
        self.added: list[dict] = []

    async def add(self, **fields) -> SimpleNamespace:
        self.added.append(fields)
        return SimpleNamespace(**fields)


class FakeLLM:
    def __init__(self, events: list[str], error: Exception | None = None) -> None:
        self.events = events
        self.error = error
        self.calls: list[tuple[list[ChatMessage], str]] = []

    async def chat(self, messages: Sequence[ChatMessage], model: str) -> ChatResult:
        self.events.append("llm")
        self.calls.append((list(messages), model))
        if self.error:
            raise self.error
        return ChatResult(
            content="hello back",
            model="provider/reported-model",
            generation_id="gen-1",
            finish_reason="stop",
            prompt_tokens=5,
            completion_tokens=7,
            cost=0.0001,
            latency_ms=123,
        )


class Harness:
    def __init__(self, *, found: bool = True, llm_error: Exception | None = None, limit: int = 20):
        self.events: list[str] = []
        self.session = FakeSession(self.events)
        self.conversations = FakeConversationRepository(SimpleNamespace() if found else None)
        self.messages = FakeMessageRepository(self.events)
        self.metrics = FakeMetricRepository()
        self.llm = FakeLLM(self.events, llm_error)
        self.service = ChatService(
            self.session,  # type: ignore[arg-type]
            self.conversations,  # type: ignore[arg-type]
            self.messages,  # type: ignore[arg-type]
            self.metrics,  # type: ignore[arg-type]
            self.llm,
            history_limit=limit,
        )


async def test_unknown_conversation_raises_and_saves_nothing():
    h = Harness(found=False)

    with pytest.raises(ConversationNotFoundError):
        await h.service.send_message(uuid.uuid4(), "hi", MODEL)

    assert h.messages.stored == []
    assert h.session.commits == 0
    assert h.llm.calls == []


async def test_happy_path_saves_both_messages_and_metric_with_two_commits():
    h = Harness()
    conversation_id = uuid.uuid4()

    result = await h.service.send_message(conversation_id, "hi", MODEL)

    assert result.role == "assistant"
    assert result.content == "hello back"
    assert [m.role for m in h.messages.stored] == ["user", "assistant"]
    assert h.messages.stored[0].model is None
    assert h.session.commits == 2
    assert h.conversations.touched == 2
    assert h.metrics.added == [
        {
            "message_id": result.id,
            "generation_id": "gen-1",
            "finish_reason": "stop",
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "cost": 0.0001,
            "latency_ms": 123,
        }
    ]


async def test_user_message_is_committed_before_the_llm_call():
    h = Harness()

    await h.service.send_message(uuid.uuid4(), "hi", MODEL)

    assert h.events.index("commit") < h.events.index("llm")
    assert h.events[-1] == "commit"


async def test_history_is_mapped_and_capped():
    h = Harness(limit=3)
    cid = uuid.uuid4()
    for i in range(5):
        await h.messages.add(f"old-{i}", cid, "user", None)
    h.messages.stored.append(Message(id=uuid.uuid4(), content="x", role="tool", model="m"))

    await h.service.send_message(cid, "latest", MODEL)

    sent, model = h.llm.calls[0]
    assert h.messages.last_limit == 3
    assert model == MODEL
    assert all(isinstance(m, ChatMessage) for m in sent)
    assert [m.role for m in sent] == ["user", "user"]  # tool message skipped
    assert sent[-1].content == "latest"


async def test_llm_failure_keeps_user_message_and_saves_no_assistant():
    h = Harness(llm_error=LLMServerError("boom"))

    with pytest.raises(LLMServerError):
        await h.service.send_message(uuid.uuid4(), "hi", MODEL)

    assert [m.role for m in h.messages.stored] == ["user"]
    assert h.session.commits == 1
    assert h.metrics.added == []


async def test_assistant_message_uses_model_reported_by_provider():
    h = Harness()

    result = await h.service.send_message(uuid.uuid4(), "hi", MODEL)

    assert result.model == "provider/reported-model"
