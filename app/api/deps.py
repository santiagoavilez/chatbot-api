from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm import LLMClient
from app.clients.openrouter import OpenRouterClient
from app.db.session import get_db
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.message_metric import MessageMetricRepository
from app.services.chat import ChatService


def get_llm_client(request: Request) -> LLMClient:
    return OpenRouterClient(request.app.state.http_client)


def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> ChatService:
    return ChatService(
        session=session,
        conversations=ConversationRepository(session),
        messages=MessageRepository(session),
        metrics=MessageMetricRepository(session),
        llm=llm,
    )


DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
