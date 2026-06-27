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
    # A substantial block of genuinely new text (a new post, job, feature, or
    # announcement) is a meaningful change even when overall page similarity stays
    # high — this catches incremental additions that full-page embeddings miss.
    # A reword nets ~0 new chars, so cosmetic noise stays below this.
    min_new_content_chars: int = 120

    # Scheduler (in-process APScheduler). Off by default so tests/dev don't fire
    # background scrapes; the production pipeline runs via GitHub Actions instead.
    enable_scheduler: bool = False
    scrape_interval_hours: int = 6

    # LLM impact scoring via Ollama. Runtime CPU-feature detection means the same
    # model runs on dev, CI, and the deploy host without instruction-set crashes.
    # llama3.2 = Llama-3.2-3B-Instruct Q4 (~2 GB), ~20s/change on a CPU.
    llm_enabled: bool = True
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "llama3.2"
    llm_temperature: float = 0.2

    # Notion CRM. Sync is auto-skipped until both are set, so the app runs fine
    # without Notion configured. Idempotency is keyed on the change id.
    notion_token: str = ""
    notion_database_id: str = ""

    # Digest email (SMTP). Auto-skipped until host+user+password+recipient set.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    digest_from: str = ""  # defaults to smtp_user
    digest_to: str = ""
    digest_frequency: str = "daily"  # daily | weekly (the cron drives actual cadence)

    # API key for the Chrome extension / external clients. Empty = endpoints open
    # (dev); set = guarded endpoints require a matching X-API-Key header.
    api_key: str = ""


settings = Settings()
