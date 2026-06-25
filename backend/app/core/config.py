"""Application configuration, loaded from environment / .env.

Everything tunable lives here so a stranger can see every knob in one place.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Argus"
    environment: str = "development"

    # Local dev defaults to the docker-compose Postgres (see docker-compose.yml).
    # In production this is overridden by a hosted Postgres URL (Neon/Supabase).
    database_url: str = "postgresql+asyncpg://argus:argus@localhost:5432/argus"

    # Scraper behaviour. A real browser-ish UA gets us past naive UA gating
    # without needing a paid proxy (a hard constraint of the assignment).
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ArgusBot/0.1"
    )
    request_timeout_seconds: float = 20.0


settings = Settings()
