from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
DBSession = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with DBSession() as session:
        yield session
