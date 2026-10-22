import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.http import create_openrouter_http_client
from app.db.session import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # --- startup: runs ONCE, before the first request ---
    app.state.http_client = create_openrouter_http_client()

    yield

    try:
        app.state.http_client.aclose()
        await asyncio.sleep(0.1)
        await engine.dispose()
    except Exception:
        logger.exception("Error closing HTTP client")
    finally:
        pass


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
