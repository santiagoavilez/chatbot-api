import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from app.api.deps import get_chat_service
from app.core.exceptions import (
    ConversationNotFoundError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServerError,
)
from app.main import app
from app.models import Message

MODEL = "google/gemma-4-31b-it:free"
PROVIDER_SECRET = "provider said: key sk-or-v1-secret is invalid"


class FakeChatService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[uuid.UUID, str, str]] = []

    async def send_message(self, conversation_id: uuid.UUID, content: str, model: str) -> Message:
        self.calls.append((conversation_id, content, model))
        if self.error:
            raise self.error
        return Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            content="hello back",
            role="assistant",
            model=model,
            created_at=datetime.now(UTC),
        )


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def use_service(service: FakeChatService) -> None:
    app.dependency_overrides[get_chat_service] = lambda: service


def url(conversation_id: uuid.UUID | None = None) -> str:
    return f"/conversations/{conversation_id or uuid.uuid4()}/messages"


async def test_creates_message_and_returns_assistant_message(client):
    service = FakeChatService()
    use_service(service)
    conversation_id = uuid.uuid4()

    response = await client.post(url(conversation_id), json={"content": "hi", "model": MODEL})

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "content", "conversation_id", "role", "model", "created_at"}
    assert body["role"] == "assistant"
    assert body["conversation_id"] == str(conversation_id)
    assert service.calls == [(conversation_id, "hi", MODEL)]


async def test_unknown_conversation_maps_to_404(client):
    use_service(FakeChatService(ConversationNotFoundError("missing")))

    response = await client.post(url(), json={"content": "hi", "model": MODEL})

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}


async def test_rate_limit_maps_to_429_with_retry_after(client):
    use_service(FakeChatService(LLMRateLimitError(PROVIDER_SECRET, 429, retry_after=12)))

    response = await client.post(url(), json={"content": "hi", "model": MODEL})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "12"


async def test_rate_limit_without_retry_after_has_no_header(client):
    use_service(FakeChatService(LLMRateLimitError("slow down", 429)))

    response = await client.post(url(), json={"content": "hi", "model": MODEL})

    assert response.status_code == 429
    assert "retry-after" not in response.headers


async def test_provider_server_error_maps_to_502(client):
    use_service(FakeChatService(LLMServerError("upstream down", 500)))

    response = await client.post(url(), json={"content": "hi", "model": MODEL})

    assert response.status_code == 502


async def test_unclassified_provider_error_maps_to_502(client):
    use_service(FakeChatService(LLMProviderError("???")))

    response = await client.post(url(), json={"content": "hi", "model": MODEL})

    assert response.status_code == 502


async def test_provider_message_is_not_leaked(client):
    use_service(FakeChatService(LLMServerError(PROVIDER_SECRET, 500)))

    response = await client.post(url(), json={"content": "hi", "model": MODEL})

    assert "sk-or" not in response.text
    assert "provider said" not in response.text
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize(
    "payload",
    [
        {"content": "", "model": MODEL},
        {"content": "   ", "model": MODEL},
        {"content": "hi", "model": "not/allowed"},
        {"content": "hi"},
    ],
)
async def test_invalid_body_returns_422(client, payload):
    service = FakeChatService()
    use_service(service)

    response = await client.post(url(), json=payload)

    assert response.status_code == 422
    assert service.calls == []
