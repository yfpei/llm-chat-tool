import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db, async_session
from app.deps import get_current_user
from app.models import Message, Conversation, User, UserKeyOverride
from app.schemas import ChatRequest
from app.services.chat_service import get_conversation_with_key, truncate_messages
from app.services.llm import create_provider
from app.services.key_service import get_decrypted_key

XINGHUO_THINKING_PROMPT = (
    "你能够回答用户的各种问题，回答问题能够角度全面、表述专业、重点突出。"
    "当前是慢思考模式，请你先深入剖析给出问题的关键要点与内在逻辑，生成思考过程，"
    "再根据思考过程回答给出问题。"
    "思考过程以<unused6>开头，在结尾处用<unused7>标注结束，"
    "<unused7>后为基于思考过程的回答内容"
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conversation_id}")
async def chat(
    conversation_id: str,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv, api_key = await get_conversation_with_key(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key，请先添加并激活一个 API Key")

    # Apply user overrides for shared keys
    if api_key.user_id is None:
        result = await db.execute(
            select(UserKeyOverride).where(
                UserKeyOverride.user_id == current_user.id,
                UserKeyOverride.api_key_id == api_key.id,
            )
        )
        override = result.scalar_one_or_none()
        if override:
            if override.enable_thinking is not None:
                api_key.enable_thinking = override.enable_thinking
            if override.max_context_tokens is not None:
                api_key.max_context_tokens = override.max_context_tokens

    # Save user message
    user_msg = Message(conversation_id=conversation_id, role="user", content=req.content)
    db.add(user_msg)
    conv.updated_at = datetime.utcnow()
    await db.commit()

    # Build context
    await db.refresh(conv, ["messages"])
    messages = [{"role": m.role, "content": m.content} for m in conv.messages]
    messages = truncate_messages(messages, api_key.max_context_tokens, api_key.provider)

    # For X1 model type, inject thinking prompt instead of using native thinking
    use_native_thinking = api_key.enable_thinking
    if api_key.enable_thinking and api_key.model_type == "x1":
        messages.insert(0, {"role": "system", "content": XINGHUO_THINKING_PROMPT})
        use_native_thinking = False

    # Create provider
    plaintext_key = get_decrypted_key(api_key)
    provider = create_provider(api_key.provider, api_key.base_url, plaintext_key, api_key.model, use_native_thinking)

    user_content = req.content

    async def event_generator():
        full_response = ""
        try:
            async for chunk in provider.chat_stream(messages):
                full_response += chunk
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "chunk", "content": chunk}),
                }

            async with async_session() as session:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                )
                session.add(assistant_msg)

                conv_obj = await session.get(Conversation, conversation_id)
                if conv_obj:
                    conv_obj.updated_at = datetime.utcnow()
                    if conv_obj.title == "新会话" and user_content:
                        conv_obj.title = user_content[:10]

                await session.commit()

            # 发送 usage 信息（如果有）
            if provider.usage:
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "usage", "content": provider.usage}),
                }

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
