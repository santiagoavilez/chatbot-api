import asyncio
import uuid

from app.db.session import DBSession
from app.models import Message
from app.repositories.conversation import ConversationRepository


async def main():
    async with DBSession() as session:
        repo = ConversationRepository(session)
        hello = await repo.create("Hello world!")
        await repo.create("hola mundo!")
        await repo.create("Hola amigo")

        select = await repo.get(hello.id)
        print(select.updated_at)
        print("cambiando titulo")
        await repo.update_title(select.id, "Cambio de titulo")
        print(select.updated_at)

        await repo.get(uuid.uuid4())

        message = Message(conversation_id=select.id, role="user", content="Hello chat bot")
        message2 = Message(conversation_id=hello.id, role="user", content="hi")
        session.add(message)
        session.add(message2)

        await repo.list_recent(limit=3, offset=0)
        delete_ramdom = await repo.delete(uuid.uuid4())
        await session.commit()

        print(select.title)
        print(delete_ramdom)

    async with DBSession() as second:
        repo2 = ConversationRepository(second)
        return_delete = await repo2.delete(select.id)
        await second.commit()
        print(return_delete)
    async with DBSession() as third:
        repo3 = ConversationRepository(third)
        select_conversation_deleted = await repo3.get(select.id)
        select_message_deleted = await third.get(Message, message2.id)

        print(select_conversation_deleted)
        print(select_message_deleted)


asyncio.run(main())
