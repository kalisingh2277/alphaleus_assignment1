"""Global intelligence feed — all detected changes, filterable.

Backs the assignment's "intelligence feed" view. Defaults to meaningful changes
only; pass ``meaningful_only=false`` to also see what the noise filter caught.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import require_api_key
from app.models.app_state import STATE_ID, AppState
from app.models.change import Change, ChangeCategory
from app.schemas.competitor import ChangeOut

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("/unread-count", dependencies=[Depends(require_api_key)])
async def unread_count(session: AsyncSession = Depends(get_session)) -> dict:
    """Number of meaningful changes since the feed was last viewed (badge count)."""
    state = await session.get(AppState, STATE_ID)
    stmt = select(func.count()).select_from(Change).where(Change.is_meaningful.is_(True))
    if state is not None and state.last_feed_viewed_at is not None:
        stmt = stmt.where(Change.detected_at > state.last_feed_viewed_at)
    return {"unread": (await session.execute(stmt)).scalar_one()}


@router.post("/mark-read")
async def mark_read(session: AsyncSession = Depends(get_session)) -> dict:
    """Mark the feed as viewed now (resets the unread badge)."""
    state = await session.get(AppState, STATE_ID)
    if state is None:
        state = AppState(id=STATE_ID)
        session.add(state)
    state.last_feed_viewed_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.get("", response_model=list[ChangeOut])
async def feed(
    competitor_id: uuid.UUID | None = None,
    category: ChangeCategory | None = None,
    meaningful_only: bool = True,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Change)
    if competitor_id is not None:
        stmt = stmt.where(Change.competitor_id == competitor_id)
    if category is not None:
        stmt = stmt.where(Change.category == category)
    if meaningful_only:
        stmt = stmt.where(Change.is_meaningful.is_(True))
    stmt = stmt.order_by(Change.detected_at.desc()).limit(limit)
    return (await session.execute(stmt)).scalars().all()
