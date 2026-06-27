"""API-key guard for the Chrome extension / external clients.

When ``API_KEY`` is unset the guard is a no-op (convenient for local dev). When
set, guarded endpoints require a matching ``X-API-Key`` header.
"""

from fastapi import Header, HTTPException

from app.core.config import settings


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
