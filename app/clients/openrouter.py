import httpx

from pydantic import BaseModel


class _Message(BaseModel):
    """Private schema for OpenRouter response messages"""

    content: str | None


class _Usage(BaseModel):
    """Private schema for OpenRouter response usage statistics"""

    prompt_tokens: int
    completion_tokens: int
    cost: float | None = None


class _Choice(BaseModel):
    """Private schema for OpenRouter response choices"""

    message: _Message
    finish_reason: str


class _ChatCompletion(BaseModel):
    """Private schema for the full OpenRouter chat completion response"""

    id: str
    choices: list[_Choice]
    usage: _Usage
    model: str


class OpenRouterClient:
    """Concrete LLM adapter for OpenRouter"""
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client