"""Global intelligence feed — all detected changes, filterable.

Backs the assignment's "intelligence feed" view. Defaults to meaningful changes
only; pass ``meaningful_only=false`` to also see what the noise filter caught.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.change import Change, ChangeCategory
from app.schemas.competitor import ChangeOut

router = APIRouter(prefix="/changes", tags=["changes"])


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
