import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # --- startup: runs ONCE, before the first request ---
    # TODO: create ONE httpx.AsyncClient
    global http_client
    http_client = httpx.AsyncClient(
        base_url=settings.open_router_base_url,
        headers={
            "Authorization": f"Bearer {settings.open_router_api_key.get_secret_value()}",
        },
        timeout=settings.open_router_timeout,
    )

    yield
    # --- shutdown: runs ONCE, when the server stops ---
    # TODO: close the HTTP client (it's async: aclose)
    await http_client.aclose()
    await engine.dispose()  # ← dispose the engine


app = FastAPI(title="Chatbot API", version="0.1.0", lifespan=lifespan)
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2)
    except Exception:
        logger.exception("Readiness check failed")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not ready"
        ) from None
    return {"status": "ready"}
