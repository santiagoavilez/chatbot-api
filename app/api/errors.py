import logging
import math

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConversationNotFoundError,
    DomainError,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentBlockedError,
    LLMInsufficientCreditsError,
    LLMInvalidRequestError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

# Domain exception -> (HTTP status, our own generic message). Provider messages are never
# echoed to the client. Subclass lookup follows the MRO, so LLMProviderError is the fallback.
_ERROR_MAP: dict[type[DomainError], tuple[int, str]] = {
    ConversationNotFoundError: (status.HTTP_404_NOT_FOUND, "Conversation not found"),
    LLMRateLimitError: (status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit reached, retry later"),
    LLMTimeoutError: (status.HTTP_504_GATEWAY_TIMEOUT, "The language model timed out"),
    LLMContentBlockedError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "The request was blocked by content moderation",
    ),
    LLMConnectionError: (status.HTTP_502_BAD_GATEWAY, "The language model is unreachable"),
    LLMServerError: (status.HTTP_502_BAD_GATEWAY, "The language model failed"),
    LLMInvalidResponseError: (
        status.HTTP_502_BAD_GATEWAY,
        "The language model returned an invalid response",
    ),
    LLMAuthenticationError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "The language model service is temporarily unavailable",
    ),
    LLMInsufficientCreditsError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "The language model service is temporarily unavailable",
    ),
    LLMInvalidRequestError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error"),
    LLMProviderError: (status.HTTP_502_BAD_GATEWAY, "The language model failed"),
}


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    status_code, detail = next(_ERROR_MAP[cls] for cls in type(exc).__mro__ if cls in _ERROR_MAP)
    logger.warning(
        "Domain error %s mapped to HTTP %s (provider_status=%s): %s",
        type(exc).__name__,
        status_code,
        getattr(exc, "status_code", None),
        getattr(exc, "message", str(exc)),
    )
    headers = None
    retry_after = getattr(exc, "retry_after", None)
    if isinstance(exc, LLMRateLimitError) and retry_after is not None:
        headers = {"Retry-After": str(math.ceil(retry_after))}
    return JSONResponse({"detail": detail}, status_code=status_code, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    for exc_class in _ERROR_MAP:
        app.add_exception_handler(exc_class, _handle_domain_error)
