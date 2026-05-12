from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, ApiKey, User
from app.utils.token_counter import count_tokens


def truncate_messages(messages: list[dict], max_tokens: int, provider: str) -> list[dict]:
    """Remove oldest non-system messages until total tokens <= max_tokens."""
    total = count_tokens(messages, provider)
    if total <= max_tokens:
        return messages

    # Separate system messages and chat messages
    system_msgs = [m for m in messages if m["role"] == "system"]
    chat_msgs = [m for m in messages if m["role"] != "system"]

    # Remove from the front of chat_msgs until under limit
    while chat_msgs and count_tokens(system_msgs + chat_msgs, provider) > max_tokens:
        chat_msgs.pop(0)

    return system_msgs + chat_msgs


async def get_conversation_with_key(db: AsyncSession, conversation_id: str, user: User | None = None):
    """Load conversation with messages and associated API key."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return None, None

    api_key = None
    if conv.api_key_id:
        api_key = await db.get(ApiKey, conv.api_key_id)
    elif user and user.active_key_id:
        api_key = await db.get(ApiKey, user.active_key_id)

    return conv, api_key
