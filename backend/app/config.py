from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    encryption_key: str
    database_url: str = "sqlite+aiosqlite:///./llm_chat.db"


settings = Settings()
