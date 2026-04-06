from typing import AsyncGenerator

import anthropic

from app.services.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        super().__init__(base_url, api_key, model)
        self.client = anthropic.AsyncAnthropic(base_url=base_url, api_key=api_key)

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        # Anthropic requires separating system message
        system_content = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }
        if system_content:
            kwargs["system"] = system_content

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
