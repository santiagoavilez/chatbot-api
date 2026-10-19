import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self, content: str, conversation_id: uuid.UUID, role: str, model: str | None
    ) -> Message:
        new_message = Message(
            content=content, conversation_id=conversation_id, role=role, model=model
        )
        self.session.add(new_message)
        await self.session.flush()
        return new_message

    async def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int, offset: int
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        message_list = result.scalars().all()
        cronological_messages = list(reversed(message_list))
        return cronological_messages
