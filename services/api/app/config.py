from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Map Railway/Heroku-style Postgres URLs to SQLAlchemy + psycopg v3."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class Settings(BaseSettings):
    """Environment contract for the API. Secrets stay out of the repo."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # openai | anthropic | stub (stub = local deterministic, no external calls)
    llm_provider: str = "stub"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    model_name: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 1

    database_url: str = "sqlite:///./local.db"
    # Comma-separated browser origins allowed to call the API (set to Vercel URL in prod)
    cors_origins: str = "http://localhost:3000"

    # 0 disables rate limiting
    rate_limit_per_minute: int = 30

    @property
    def sqlalchemy_database_url(self) -> str:
        return normalize_database_url(self.database_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
