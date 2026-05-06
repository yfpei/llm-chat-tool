from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    from sqlalchemy import text

    async with engine.begin() as conn:
        from app.models import ApiKey, Conversation, Message, BatchTask  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add is_xinghuo_x1 column for existing databases
        try:
            await conn.execute(text("ALTER TABLE api_keys ADD COLUMN is_xinghuo_x1 BOOLEAN DEFAULT 0"))
        except Exception:
            pass
