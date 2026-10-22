import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, title: str | None) -> Conversation:
        new_conversation = Conversation(title=title)
        self.session.add(new_conversation)
        await self.session.flush()
        return new_conversation

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def list_recent(self, limit: int, offset: int) -> Sequence[Conversation]:
        stmt = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc(), Conversation.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        conversation_list = result.scalars().all()
        return conversation_list

    async def update_title(self, conversation_id: uuid.UUID, title: str) -> Conversation | None:
        conversation = await self.get(conversation_id)
        if conversation is None:
            return conversation
        conversation.title = title
        await self.session.flush()
        return conversation

    async def delete(self, conversation_id: uuid.UUID) -> bool:
        conversation = await self.get(conversation_id)
        if conversation is None:
            return False
        await self.session.delete(conversation)
        await self.session.flush()
        return True

    async def touch(self, conversation: Conversation) -> None:
        """Bump ``updated_at``; ``onupdate`` does not fire when only messages change."""
        conversation.updated_at = func.now()
        await self.session.flush()
