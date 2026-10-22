import time
from collections.abc import Sequence

import httpx
from pydantic import BaseModel, ValidationError

from app.clients.llm import ChatMessage, ChatResult
from app.core.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentBlockedError,
    LLMInsufficientCreditsError,
    LLMInvalidRequestError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
)


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

    async def chat(self, messages: Sequence[ChatMessage], model: str) -> ChatResult:

        messages_dict = [m.model_dump() for m in messages]
        payload = {"model": model, "messages": messages_dict}

        start_time = time.perf_counter()

        try:
            response = await self._http_client.post("/chat/completions", json=payload)
        except httpx.ConnectError as e:
            raise LLMConnectionError("OpenRouter connection error") from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError("OpenRouter timeout error") from e
        except httpx.RequestError as e:
            raise LLMServerError("OpenRouter request error") from e

        latency_seconds = time.perf_counter() - start_time
        latency_ms = int(latency_seconds * 1000)

        self._raise_for_status(response)

        try:
            response_data = response.json()
            validated = _ChatCompletion.model_validate(response_data)
        except (ValidationError, ValueError) as e:
            raise LLMInvalidResponseError("OpenRouter invalid response") from e

        # check choices length
        if len(validated.choices) == 0:
            raise LLMInvalidResponseError("OpenRouter empty response")
        first_choice = validated.choices[0]
        finish_reason = first_choice.finish_reason
        content = first_choice.message.content
        usage = validated.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        cost = usage.cost
        if finish_reason == "content_filter":
            raise LLMContentBlockedError("OpenRouter content filter")
        if finish_reason == "error":
            raise LLMServerError("OpenRouter error")
        if not content:
            raise LLMInvalidResponseError("OpenRouter empty response")

        return ChatResult(
            content=content,
            model=validated.model,
            generation_id=validated.id,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _parse_error(response: httpx.Response) -> tuple[str, bool]:
        """
        Defensively extracts the error message and moderation status from the response payload.
        """
        message = f"OpenRouter request failed with status code {response.status_code}"
        is_moderation = False

        try:
            payload = response.json()
            error_obj = payload["error"]

            # Extract message
            if raw_msg := error_obj.get("message"):
                if isinstance(raw_msg, str) and raw_msg.strip():
                    message = raw_msg

            # Check moderation signals documented by OpenRouter metadata
            metadata = error_obj.get("metadata", {})
            if isinstance(metadata, dict):
                has_reasons = bool(metadata.get("reasons"))
                has_flagged_input = bool(metadata.get("flagged_input"))
                is_moderation = has_reasons or has_flagged_input

        except (ValueError, KeyError, TypeError):
            pass  # Non-JSON response, missing 'error' key, or wrong structural types

        return message, is_moderation

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Inspects the HTTP response and raises the corresponding domain exception on failure."""
        if response.is_success:
            return

        status = response.status_code
        message, is_moderation = self._parse_error(response)

        match status:
            case 400 | 404:
                raise LLMInvalidRequestError(message, status_code=status)

            case 401:
                raise LLMAuthenticationError(message, status_code=status)

            case 402:
                raise LLMInsufficientCreditsError(message, status_code=status)

            case 403:
                if is_moderation:
                    raise LLMContentBlockedError(message, status_code=status)
                raise LLMAuthenticationError(message, status_code=status)

            case 408 | 504:
                raise LLMTimeoutError(message, status_code=status)

            case 429:
                retry_after: float | None = None
                if retry_after_str := response.headers.get("Retry-After"):
                    try:
                        retry_after = float(retry_after_str)
                    except ValueError:
                        retry_after = None

                raise LLMRateLimitError(
                    message,
                    status_code=status,
                    retry_after=retry_after,
                )

            case s if s >= 500:
                raise LLMServerError(message, status_code=status)

            case s if 400 <= s < 500:
                raise LLMInvalidRequestError(message, status_code=status)

            case _:
                raise LLMServerError(message, status_code=status)
