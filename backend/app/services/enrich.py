"""Enrichment pass: score meaningful, not-yet-scored changes with the LLM.

Runs after detection in the pipeline. It also naturally *retries* any change the
LLM couldn't score on a previous run (summary still NULL), so a transient Ollama
outage doesn't lose a card — it gets picked up next run.
"""

from __future__ import annotations

import contextlib

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business import SINGLETON_ID, BusinessProfile
from app.models.change import Change, ChangeCategory
from app.models.competitor import Competitor
from app.models.snapshot import PageSnapshot
from app.services import llm
from app.services.classifier import changed_text

log = structlog.get_logger()


async def _profile_dict(session: AsyncSession) -> dict:
    profile = await session.get(BusinessProfile, SINGLETON_ID)
    if profile is None:
        return {"product": "", "customers": "", "price_point": ""}
    return {
        "product": profile.product,
        "customers": profile.customers,
        "price_point": profile.price_point,
    }


async def _detail(session: AsyncSession, change: Change) -> str:
    """A human-readable description of what changed, for the LLM prompt."""
    if change.structured_diff and "prices" in change.structured_diff:
        delta = change.structured_diff["prices"].get("delta")
        if delta:
            return f"Price change: {delta}"
    to_snap = await session.get(PageSnapshot, change.to_snapshot_id)
    from_snap = (
        await session.get(PageSnapshot, change.from_snapshot_id)
        if change.from_snapshot_id
        else None
    )
    if from_snap and to_snap:
        excerpt = changed_text(from_snap.clean_text, to_snap.clean_text)
        if excerpt:
            return excerpt[:1500]
    return to_snap.clean_text[:1500] if to_snap else ""


async def enrich_pending(session: AsyncSession) -> dict:
    """Score every meaningful change that has no summary yet."""
    stats = {"scored": 0, "llm_errors": 0}
    if not settings.llm_enabled:
        return stats

    profile = await _profile_dict(session)
    pending = (
        await session.execute(
            select(Change)
            .where(Change.is_meaningful.is_(True), Change.summary.is_(None))
            .order_by(Change.detected_at.asc())
        )
    ).scalars().all()

    for change in pending:
        competitor = await session.get(Competitor, change.competitor_id)
        detail = await _detail(session, change)
        try:
            result = await llm.score_change(
                profile,
                competitor.name if competitor else "Unknown",
                detail,
            )
        except llm.LLMError as exc:
            stats["llm_errors"] += 1
            log.warning("llm_score_failed", change_id=str(change.id), error=str(exc))
            continue

        change.summary = result.summary
        change.impact_score = result.impact_score
        change.impact_justification = result.impact_justification
        change.recommended_action = result.recommended_action
        # The LLM is the authoritative classifier; it refines the fast embeddings
        # guess made at detection time. Keep the guess if the LLM returns something odd.
        with contextlib.suppress(ValueError):
            change.category = ChangeCategory(result.category)
        stats["scored"] += 1

    await session.commit()
    return stats
