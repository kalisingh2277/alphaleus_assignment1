"""Competitor + snapshot endpoints — the Day 1 vertical slice.

Add a URL, scrape it on demand, and read back the scraped content / history.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.competitor import Competitor, MonitorStatus
from app.models.snapshot import PageSnapshot
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorOut,
    ScrapeResult,
    SnapshotOut,
)
from app.services import scraper

router = APIRouter(prefix="/competitors", tags=["competitors"])


async def _get_or_404(session: AsyncSession, competitor_id: uuid.UUID) -> Competitor:
    competitor = await session.get(Competitor, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.post("", response_model=CompetitorOut, status_code=201)
async def add_competitor(
    payload: CompetitorCreate, session: AsyncSession = Depends(get_session)
) -> Competitor:
    competitor = Competitor(
        name=payload.name,
        url=str(payload.url),
        monitor_scope=payload.monitor_scope,
    )
    session.add(competitor)
    await session.commit()
    await session.refresh(competitor)
    return competitor


@router.get("", response_model=list[CompetitorOut])
async def list_competitors(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Competitor).order_by(Competitor.created_at.desc()))
    return result.scalars().all()


@router.get("/{competitor_id}", response_model=CompetitorOut)
async def get_competitor(
    competitor_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Competitor:
    return await _get_or_404(session, competitor_id)


@router.post("/{competitor_id}/scrape", response_model=ScrapeResult)
async def scrape_now(
    competitor_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ScrapeResult:
    """Scrape the page right now, store a snapshot, and report whether it changed."""
    competitor = await _get_or_404(session, competitor_id)

    prev = (
        await session.execute(
            select(PageSnapshot)
            .where(PageSnapshot.competitor_id == competitor_id)
            .order_by(PageSnapshot.scraped_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    try:
        out = await scraper.scrape(competitor.url)
    except scraper.ScrapeError as exc:
        competitor.status = MonitorStatus.error
        competitor.last_error = str(exc)[:1000]
        competitor.last_checked_at = datetime.now(UTC)
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    snapshot = PageSnapshot(
        competitor_id=competitor.id,
        clean_text=out.clean_text,
        content_hash=out.content_hash,
        char_count=len(out.clean_text),
        http_status=out.http_status,
        extraction_method=out.extraction_method,
    )
    session.add(snapshot)
    competitor.status = MonitorStatus.active
    competitor.last_error = None
    competitor.last_checked_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(snapshot)

    return ScrapeResult(
        snapshot=SnapshotOut.model_validate(snapshot),
        is_first=prev is None,
        changed=prev is not None and prev.content_hash != out.content_hash,
        preview=out.clean_text[:500],
    )


@router.get("/{competitor_id}/snapshots", response_model=list[SnapshotOut])
async def list_snapshots(
    competitor_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    await _get_or_404(session, competitor_id)
    result = await session.execute(
        select(PageSnapshot)
        .where(PageSnapshot.competitor_id == competitor_id)
        .order_by(PageSnapshot.scraped_at.desc())
    )
    return result.scalars().all()
