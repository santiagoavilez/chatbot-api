from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    open_router_api_key: SecretStr
    database_url: SecretStr = "postgresql+asyncpg://postgres:postgres@db:5432/chatbotfastapi"
    debug: bool = True
    api_port: int = 8000


settings = Settings()
