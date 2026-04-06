from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        super().__init__(base_url, api_key, model)
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
