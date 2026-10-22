from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    """Represents a single message in a conversation sent to an LLM."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant", "system"]
    content: str


class ChatResult(BaseModel):
    """Normalized response payload returned by an LLM provider."""

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    generation_id: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    cost: float | None = None
    latency_ms: float


class LLMClient(Protocol):
    """Abstract interface (Protocol) that every concrete LLM adapter must implement."""

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        model: str,
    ) -> ChatResult: ...
