import asyncio
import logging

from app.clients.http import create_openrouter_http_client
from app.clients.llm import ChatMessage
from app.clients.openrouter import OpenRouterClient
from app.core.exceptions import LLMProviderError, LLMRateLimitError

# Configuramos un logger básico
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


async def main() -> None:
    # El bloque `async with` gestiona la apertura y el cierre limpio del cliente
    async with create_openrouter_http_client() as http_client:
        client = OpenRouterClient(http_client)

        try:
            result = await client.chat(
                [ChatMessage(role="user", content="What is the capital of France?")],
                model=MODEL,
            )
            logger.info(f"Success! Result: {result}")

        except LLMRateLimitError as e:
            logger.warning(
                f"Rate limit exceeded (Status {e.status_code}): {e.message}. "
                f"Retry after {e.retry_after} seconds."
            )

        except LLMProviderError as e:
            logger.error(f"Provider error (Status {e.status_code}): {e.message}")

        except Exception as e:
            logger.exception(f"Unexpected critical error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
