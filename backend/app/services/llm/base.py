from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMProvider(ABC):
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Yield content chunks from the LLM response."""
        ...
