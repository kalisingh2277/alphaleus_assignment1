"""Competitor, snapshot, and change endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.change import Change
from app.models.competitor import Competitor
from app.models.snapshot import PageSnapshot
from app.schemas.competitor import (
    ChangeOut,
    CompetitorCreate,
    CompetitorOut,
    ScrapeResult,
    SnapshotOut,
)
from app.services import scraper
from app.services.ingest import ingest

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
    """Scrape now, store a snapshot, and report whether a meaningful change occurred."""
    competitor = await _get_or_404(session, competitor_id)
    try:
        outcome = await ingest(session, competitor)
    except scraper.ScrapeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    change = outcome.change
    return ScrapeResult(
        snapshot=SnapshotOut.model_validate(outcome.snapshot),
        is_first=outcome.is_first,
        changed=change is not None,
        is_meaningful=change.is_meaningful if change else False,
        similarity=change.similarity if change else None,
        category=change.category if change else None,
        structured_diff=change.structured_diff if change else None,
        preview=outcome.snapshot.clean_text[:500],
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


@router.get("/{competitor_id}/changes", response_model=list[ChangeOut])
async def list_changes(
    competitor_id: uuid.UUID,
    meaningful_only: bool = Query(False, description="Hide filtered cosmetic changes"),
    session: AsyncSession = Depends(get_session),
):
    await _get_or_404(session, competitor_id)
    stmt = select(Change).where(Change.competitor_id == competitor_id)
    if meaningful_only:
        stmt = stmt.where(Change.is_meaningful.is_(True))
    result = await session.execute(stmt.order_by(Change.detected_at.desc()))
    return result.scalars().all()
