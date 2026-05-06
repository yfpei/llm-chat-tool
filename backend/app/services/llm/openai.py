from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str, enable_thinking: bool = True):
        super().__init__(base_url, api_key, model, enable_thinking)
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._think_open = False

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        self._think_open = False
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            extra_body={"chat_template_kwargs": {"enable_thinking": self.enable_thinking}},
        )
        async for chunk in stream:
            if hasattr(chunk, 'usage') and chunk.usage:
                self.usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }
            if chunk.choices:
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, 'reasoning_content', None) or ''
                text = delta.content or ''

                if reasoning:
                    if not self._think_open:
                        yield '<think>'
                        self._think_open = True
                    yield reasoning

                if text:
                    if self._think_open:
                        yield '</think>'
                        self._think_open = False
                    yield text

        if self._think_open:
            yield '</think>'
            self._think_open = False
