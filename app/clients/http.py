import httpx

from app.config import settings


def create_openrouter_http_client() -> httpx.AsyncClient:
    """
    Creates and configures an httpx.AsyncClient for communicating with OpenRouter.
    The caller is responsible for managing the client's lifecycle (e.g., using 'async with'
    or calling '.aclose()').
    """
    return httpx.AsyncClient(
        base_url=settings.open_router_base_url,
        headers={
            "Authorization": f"Bearer {settings.open_router_api_key.get_secret_value()}",
        },
        timeout=httpx.Timeout(settings.open_router_timeout, connect=5.0),
    )
