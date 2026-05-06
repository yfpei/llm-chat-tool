from typing import AsyncGenerator

import anthropic

from app.services.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str, enable_thinking: bool = True):
        super().__init__(base_url, api_key, model, enable_thinking)
        clean_url = base_url.rstrip("/")
        if clean_url.endswith("/v1"):
            clean_url = clean_url[:-3]
        self.client = anthropic.AsyncAnthropic(base_url=clean_url, api_key=api_key)
        self._think_open = False

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        self._think_open = False
        system_content = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }
        if system_content:
            kwargs["system"] = system_content
        if self.enable_thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2048}

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        if not self._think_open:
                            yield '<think>'
                            self._think_open = True
                        yield event.delta.thinking
                    elif event.delta.type == "text_delta":
                        if self._think_open:
                            yield '</think>'
                            self._think_open = False
                        yield event.delta.text
                elif event.type == "message_delta":
                    if hasattr(event, 'usage') and event.usage:
                        self.usage = {
                            "prompt_tokens": event.usage.input_tokens,
                            "completion_tokens": event.usage.output_tokens,
                            "total_tokens": event.usage.input_tokens + event.usage.output_tokens,
                        }

        if self._think_open:
            yield '</think>'
            self._think_open = False
