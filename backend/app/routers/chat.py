import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models import Message
from app.schemas import ChatRequest
from app.services.chat_service import get_conversation_with_key, truncate_messages
from app.services.llm import create_provider
from app.services.key_service import get_decrypted_key

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conversation_id}")
async def chat(conversation_id: str, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    conv, api_key = await get_conversation_with_key(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key，请先添加并激活一个 API Key")

    # Save user message
    user_msg = Message(conversation_id=conversation_id, role="user", content=req.content)
    db.add(user_msg)
    conv.updated_at = datetime.utcnow()
    await db.commit()

    # Build context
    await db.refresh(conv, ["messages"])
    messages = [{"role": m.role, "content": m.content} for m in conv.messages]
    messages = truncate_messages(messages, api_key.max_context_tokens, api_key.provider)

    # Create provider
    plaintext_key = get_decrypted_key(api_key)
    provider = create_provider(api_key.provider, api_key.base_url, plaintext_key, api_key.model)

    async def event_generator():
        full_response = ""
        try:
            async for chunk in provider.chat_stream(messages):
                full_response += chunk
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "chunk", "content": chunk}),
                }

            # Save assistant message after streaming completes
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.utcnow()

            # Auto-generate title from first exchange
            if conv.title == "新会话" and full_response:
                conv.title = req.content[:50]

            await db.commit()

            yield {
                "event": "message",
                "data": json.dumps({"type": "done", "content": ""}),
            }
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "content": str(e)}),
            }

    return EventSourceResponse(event_generator())
