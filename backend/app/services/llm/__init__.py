from app.services.llm.base import LLMProvider
from app.services.llm.openai import OpenAIProvider
from app.services.llm.anthropic import AnthropicProvider


def create_provider(provider: str, base_url: str, api_key: str, model: str, enable_thinking: bool = True) -> LLMProvider:
    if provider == "openai":
        return OpenAIProvider(base_url=base_url, api_key=api_key, model=model, enable_thinking=enable_thinking)
    elif provider == "anthropic":
        return AnthropicProvider(base_url=base_url, api_key=api_key, model=model, enable_thinking=enable_thinking)
    else:
        raise ValueError(f"Unknown provider: {provider}")
