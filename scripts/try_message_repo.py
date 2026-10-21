import asyncio

from sqlalchemy.exc import IntegrityError

from app.db.session import DBSession
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


async def main():
    # --- Block 1: create a conversation + 5 messages, then commit ---
    async with DBSession() as session:
        conversations = ConversationRepository(session)
        messages = MessageRepository(session)

        conversation = await conversations.create("Test")
        await messages.add(content="msg0", conversation_id=conversation.id, role="user", model=None)
        await messages.add(
            content="msg1",
            conversation_id=conversation.id,
            role="assistant",
            model="google/gemma-4-31b-it:free",
        )
        await messages.add(content="msg2", conversation_id=conversation.id, role="user", model=None)
        await messages.add(
            content="msg3",
            conversation_id=conversation.id,
            role="assistant",
            model="google/gemma-4-31b-it:free",
        )
        await messages.add(content="msg4", conversation_id=conversation.id, role="user", model=None)

        await session.commit()
        conversation_id = conversation.id

    # --- Block 2: read the last 3 with a NEW session ---
    async with DBSession() as session:
        messages = MessageRepository(session)
        list_by_conversation = await messages.list_by_conversation(
            conversation_id, limit=3, offset=0
        )
        print(list_by_conversation)

    # --- Block 3: break the constraint on purpose ---
    async with DBSession() as session:
        messages = MessageRepository(session)
        try:
            await messages.add(
                content="msg5",
                conversation_id=conversation_id,
                role="user",
                model="google/gemma-4-31b-it:free",
            )
            await session.commit()
            print("❌ should not get here")
        except IntegrityError as exc:
            print("✅ rejected by the database:")
            print(exc.orig)


asyncio.run(main())
