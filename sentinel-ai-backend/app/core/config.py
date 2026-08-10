"""
Application configuration, loaded from environment variables / .env.
Per the approved architecture (Section 12) and hackathon Step 6/13:
no secrets hardcoded, everything overridable via env for dev/demo/CI.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Sentinel AI"
    app_version: str = "0.1.0-phase1"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ai"
    database_url_sync: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_ai"

    # Auth
    secret_key: str = "dev-only-secret-change-me"  # noqa: S105 - overridden via env in real deployment
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS — frontend is built separately (Next.js), so this stays permissive for the hackathon
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:5173", "*"]

    # Ingestion
    uploads_dir: str = "/mnt/user-data/uploads"

    # LLM (optional — Copilot falls back to deterministic responses when unset)
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: int = 15

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
