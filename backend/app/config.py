from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "QAAI"
    environment: str = "development"
    api_prefix: str = "/api"
    enable_docs: bool = True
    rate_limit_per_minute: int = 120

    database_url: str = "mysql+pymysql://qaai:qaai@db:3306/qaai?charset=utf8mb4"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 720

    cors_origins: str = "http://localhost:3000"

    ai_enabled: bool = True
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "gemma3:270m"
    ai_timeout_seconds: float = 60.0
    ai_max_tokens: int = 400

    whisper_enabled: bool = True
    whisper_model: str = "tiny"
    max_audio_bytes: int = 20_000_000

    seed_reviewer_email: str = "reviewer@qaai.local"
    seed_reviewer_password: str = "change-me-in-production"
    seed_reviewer_name: str = "QAAI Reviewer"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
