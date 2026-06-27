"""Digest endpoint — manually trigger a digest email."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.digest import send_digest

router = APIRouter(prefix="/digest", tags=["digest"])


@router.post("/send")
async def trigger_digest(session: AsyncSession = Depends(get_session)) -> dict:
    """Send a digest of changes since the last one (suppressed if none)."""
    return await send_digest(session)
