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
        from app.models import User, ApiKey, UserKeyOverride, Conversation, Message, BatchTask, EsExportTask  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

        # --- Migrations for existing databases ---

        # Add model_type column
        try:
            await conn.execute(text("ALTER TABLE api_keys ADD COLUMN model_type VARCHAR(20)"))
        except Exception:
            pass

        # Add active_key_id to users
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN active_key_id INTEGER REFERENCES api_keys(id)"))
        except Exception:
            pass

        # Add user_id to api_keys
        try:
            await conn.execute(text("ALTER TABLE api_keys ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add user_id to conversations
        try:
            await conn.execute(text("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add user_id to batch_tasks
        try:
            await conn.execute(text("ALTER TABLE batch_tasks ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add user_id to es_export_tasks
        try:
            await conn.execute(text("ALTER TABLE es_export_tasks ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add eval_config_json column
        try:
            await conn.execute(text("ALTER TABLE batch_tasks ADD COLUMN eval_config_json TEXT"))
        except Exception:
            pass
