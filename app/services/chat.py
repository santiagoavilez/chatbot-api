import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm import ChatMessage, LLMClient
from app.core.exceptions import ConversationNotFoundError, LLMProviderError
from app.models import Conversation, Message
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.message_metric import MessageMetricRepository

_LLM_ROLES = frozenset({"user", "assistant", "system"})


class ChatService:
    """Orchestrates one chat turn and owns the transaction boundary.

    The user message is committed before the LLM call so that no database
    transaction stays open during the network request, and so that the message
    survives a provider failure.
    """

    def __init__(
        self,
        session: AsyncSession,
        conversations: ConversationRepository,
        messages: MessageRepository,
        metrics: MessageMetricRepository,
        llm: LLMClient,
        history_limit: int = 20,
    ) -> None:
        self._session = session
        self._conversations = conversations
        self._messages = messages
        self._metrics = metrics
        self._llm = llm
        self._history_limit = history_limit

    async def send_message(self, conversation_id: uuid.UUID, content: str, model: str) -> Message:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
        return await self._run_turn(conversation, content, model)

    async def start_conversation(self, content: str, model: str) -> Message:
        """Create a conversation and run its first turn.

        The conversation is committed together with the user message. If the provider
        fails, they stay saved and the error carries the new ``conversation_id``.
        """
        conversation = await self._conversations.create(title=None)
        conversation_id = conversation.id
        try:
            return await self._run_turn(conversation, content, model)
        except LLMProviderError as exc:
            exc.conversation_id = conversation_id
            raise

    async def _run_turn(self, conversation: Conversation, content: str, model: str) -> Message:
        conversation_id = conversation.id
        await self._messages.add(content, conversation_id, role="user", model=None)
        await self._conversations.touch(conversation)
        await self._session.commit()

        history = await self._build_history(conversation_id)
        result = await self._llm.chat(history, model)

        assistant_message = await self._messages.add(
            result.content, conversation_id, role="assistant", model=result.model
        )
        await self._metrics.add(
            message_id=assistant_message.id,
            generation_id=result.generation_id,
            finish_reason=result.finish_reason,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost=result.cost,
            latency_ms=int(result.latency_ms),
        )
        await self._conversations.touch(conversation)
        await self._session.commit()
        return assistant_message

    async def _build_history(self, conversation_id: uuid.UUID) -> list[ChatMessage]:
        stored = await self._messages.list_by_conversation(
            conversation_id, limit=self._history_limit, offset=0
        )
        return [
            ChatMessage(role=m.role, content=m.content)  # type: ignore[arg-type]
            for m in stored
            if m.role in _LLM_ROLES
        ]
