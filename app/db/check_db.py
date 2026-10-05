import asyncio

from sqlalchemy import text

from app.db.session import DBSession, engine


async def check_db():
    try:
        async with DBSession() as session:
            result = await session.execute(text("SELECT 1"))
            check_scalar = result.scalar_one()
            assert check_scalar == 1
            print("Database connection successful", check_scalar)
    except Exception as exc:
        raise SystemExit(f"Database check failed: {type(exc).__name__}: {exc}") from exc
    finally:
        await engine.dispose()
        print("Database connection closed")


if __name__ == "__main__":
    asyncio.run(check_db())
