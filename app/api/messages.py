import uuid

from fastapi import APIRouter, status

from app.api.deps import ChatServiceDep
from app.schemas.message import ChatRequest, MessageRead

router = APIRouter(prefix="/conversations", tags=["messages"])


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID, body: ChatRequest, service: ChatServiceDep
) -> MessageRead:
    message = await service.send_message(conversation_id, body.content, body.model)
    return MessageRead.model_validate(message)


@router.post(
    "/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_conversation(body: ChatRequest, service: ChatServiceDep) -> MessageRead:
    message = await service.start_conversation(body.content, body.model)
    return MessageRead.model_validate(message)
