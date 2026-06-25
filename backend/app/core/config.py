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

    # Change detection. A new snapshot is a "meaningful" change when its cosine
    # similarity to the previous snapshot drops BELOW this. Tuned so cosmetic
    # edits (already boilerplate-stripped) stay above it. Structured field diffs
    # (Day 2.5) override this for high-value changes embeddings smooth over.
    semantic_change_threshold: float = 0.94
    # Below this anchor-similarity the change category falls back to "other".
    classifier_min_confidence: float = 0.45

    # Scheduler (in-process APScheduler). Off by default so tests/dev don't fire
    # background scrapes; the production pipeline runs via GitHub Actions instead.
    enable_scheduler: bool = False
    scrape_interval_hours: int = 6


settings = Settings()
