"""Ingest one competitor: scrape -> embed -> store snapshot -> detect change.

This is the single code path shared by the on-demand API endpoint and the
scheduled pipeline, so detection behaves identically everywhere.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.change import Change, ChangeCategory
from app.models.competitor import Competitor, MonitorStatus
from app.models.snapshot import PageSnapshot
from app.services import classifier, embeddings, scraper, structured


@dataclass(slots=True)
class IngestOutcome:
    snapshot: PageSnapshot
    change: Change | None
    is_first: bool


async def _latest_snapshot(session: AsyncSession, competitor_id) -> PageSnapshot | None:
    return (
        await session.execute(
            select(PageSnapshot)
            .where(PageSnapshot.competitor_id == competitor_id)
            .order_by(PageSnapshot.scraped_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def ingest(session: AsyncSession, competitor: Competitor) -> IngestOutcome:
    """Scrape the competitor's page and persist a snapshot + any detected change."""
    prev = await _latest_snapshot(session, competitor.id)

    try:
        out = await scraper.scrape(competitor.url)
    except scraper.ScrapeError as exc:
        competitor.status = MonitorStatus.error
        competitor.last_error = str(exc)[:1000]
        competitor.last_checked_at = datetime.now(UTC)
        await session.commit()
        raise

    embedding = await embeddings.embed_async(out.clean_text)
    fields = structured.extract_fields(out.clean_text)
    snapshot = PageSnapshot(
        competitor_id=competitor.id,
        clean_text=out.clean_text,
        content_hash=out.content_hash,
        char_count=len(out.clean_text),
        http_status=out.http_status,
        extraction_method=out.extraction_method,
        embedding=embedding,
        structured=fields,
    )
    session.add(snapshot)
    await session.flush()  # assign snapshot.id for the FK below

    change: Change | None = None
    # Only compare when content actually differs — the hash is a free short-circuit
    # that skips the cosine math (and avoids logging "changes" with similarity 1.0).
    if prev is not None and prev.content_hash != out.content_hash:
        similarity = (
            embeddings.cosine_similarity(embedding, prev.embedding)
            if prev.embedding is not None
            else 0.0
        )
        structured_diff = structured.diff_fields(prev.structured or {}, fields)

        # Meaningful if EITHER signal fires: semantic drift OR a tracked field
        # changed. The structured signal catches what embeddings miss (pricing).
        is_meaningful = (
            similarity < settings.semantic_change_threshold or structured_diff is not None
        )

        category: ChangeCategory | None = None
        if is_meaningful:
            if structured_diff and "prices" in structured_diff:
                category = ChangeCategory.pricing  # high-confidence override
            else:
                # classify off the event loop (CPU-bound embedding work)
                category = await asyncio.to_thread(
                    classifier.classify, prev.clean_text, out.clean_text
                )

        change = Change(
            competitor_id=competitor.id,
            from_snapshot_id=prev.id,
            to_snapshot_id=snapshot.id,
            similarity=similarity,
            is_meaningful=is_meaningful,
            category=category,
            structured_diff=structured_diff,
        )
        session.add(change)

    competitor.status = MonitorStatus.active
    competitor.last_error = None
    competitor.last_checked_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(snapshot)
    if change is not None:
        await session.refresh(change)

    return IngestOutcome(snapshot=snapshot, change=change, is_first=prev is None)
