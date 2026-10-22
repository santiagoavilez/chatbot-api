class DomainError(Exception):
    """Base class for errors raised by the application's domain layer."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConversationNotFoundError(DomainError):
    """Raised when a requested conversation does not exist in the database."""


class LLMProviderError(DomainError):
    """Base exception for errors returned by or encountered while
    communicating with an LLM provider."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMConnectionError(LLMProviderError):
    """Network-level connection failure before reaching the provider (e.g., DNS failure)."""


class LLMTimeoutError(LLMProviderError):
    """Timeout waiting for the provider's response (socket timeout or upstream 408/504)."""


class LLMRateLimitError(LLMProviderError):
    """The provider rejected the request due to rate limits or quota exhaustion."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class LLMInsufficientCreditsError(LLMProviderError):
    """The provider account balance or credits have been exhausted."""


class LLMAuthenticationError(LLMProviderError):
    """Authentication or authorization failure with the provider.

    Indicates invalid API credentials or missing key permissions—a configuration problem on
    our side that the user cannot fix.
    """


class LLMContentBlockedError(LLMProviderError):
    """The request or response was blocked by moderation policies or safety guardrails.

    Indicates that input or generated content violated safety rules—a user prompt problem that
    can be resolved by rephrasing.
    """


class LLMInvalidRequestError(LLMProviderError):
    """The request sent to the provider was malformed or rejected
    (e.g., context window exceeded)."""


class LLMServerError(LLMProviderError):
    """The provider or an upstream proxy experienced an internal server error or unavailability."""


class LLMContentFilterError(LLMProviderError):
    """The request or response was blocked by moderation policies or safety guardrails."""


class LLMInvalidResponseError(LLMProviderError):
    """The provider returned HTTP 200, but the payload was malformed or broke data contracts."""
