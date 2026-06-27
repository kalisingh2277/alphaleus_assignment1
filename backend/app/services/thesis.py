"""The competitor thesis — Argus's signature feature.

Per-change cards are table stakes. The thesis is what a real analyst does:
connect a competitor's individual moves into one coherent strategy ("going
downmarket with an AI push") and say what it means for the user's business.

Cached in CompetitorThesis; regenerated only when new meaningful changes appear.
"""

from __future__ import annotations

import json

import structlog
from ollama import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business import SINGLETON_ID, BusinessProfile
from app.models.change import Change
from app.models.competitor import Competitor
from app.models.thesis import CompetitorThesis

log = structlog.get_logger()

# Need at least this many changes before a cross-change "strategy" is meaningful.
MIN_CHANGES = 2

_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "narrative": {"type": "string"},
        "recommended_focus": {"type": "string"},
    },
    "required": ["headline", "narrative", "recommended_focus"],
}

_SYSTEM = (
    "You are a competitive-intelligence analyst. Given a competitor's recent changes, "
    "synthesise them into a single STRATEGIC THESIS for the user's business: connect the "
    "dots into one coherent strategy (e.g. 'going downmarket with an AI push'), not a list. "
    "headline = 3-7 words naming the strategy. narrative = 2-3 sentences on what the "
    "competitor is doing and why it matters to the user. recommended_focus = one sentence "
    "on what the user's business should do in response."
)


async def _profile_dict(session: AsyncSession) -> dict:
    profile = await session.get(BusinessProfile, SINGLETON_ID)
    if profile is None:
        return {"product": "", "customers": "", "price_point": ""}
    return {
        "product": profile.product,
        "customers": profile.customers,
        "price_point": profile.price_point,
    }


def _format_change(c: Change) -> str:
    category = c.category.value if c.category else "other"
    return f"- [{category}] (impact {c.impact_score}/10) {c.summary}"


async def _generate(profile: dict, competitor_name: str, changes: list[Change]) -> dict:
    lines = "\n".join(_format_change(c) for c in changes)
    user = (
        f"OUR BUSINESS: {profile.get('product') or '(unspecified)'} "
        f"(customers: {profile.get('customers') or '(unspecified)'}, "
        f"price: {profile.get('price_point') or '(unspecified)'})\n\n"
        f"COMPETITOR: {competitor_name}\n"
        f"THEIR RECENT CHANGES:\n{lines}\n\n"
        "Give the single strategic thesis."
    )
    client = AsyncClient(host=settings.ollama_host)
    resp = await client.chat(
        model=settings.llm_model,
        format=_SCHEMA,
        options={"temperature": 0.3},
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
    )
    return json.loads(resp.message.content)


async def get_or_generate(session: AsyncSession, competitor: Competitor) -> CompetitorThesis | None:
    """Return the cached thesis, regenerating if new changes have arrived.

    Returns None when there aren't enough changes to synthesise a strategy yet.
    """
    changes = (
        await session.execute(
            select(Change)
            .where(
                Change.competitor_id == competitor.id,
                Change.is_meaningful.is_(True),
                Change.summary.is_not(None),
            )
            .order_by(Change.detected_at.asc())
        )
    ).scalars().all()
    if len(changes) < MIN_CHANGES:
        return None

    existing = await session.get(CompetitorThesis, competitor.id)
    if existing is not None and existing.change_count == len(changes):
        return existing

    profile = await _profile_dict(session)
    data = await _generate(profile, competitor.name, changes)
    if existing is None:
        existing = CompetitorThesis(competitor_id=competitor.id)
        session.add(existing)
    existing.headline = data.get("headline", "")
    existing.narrative = data.get("narrative", "")
    existing.recommended_focus = data.get("recommended_focus", "")
    existing.change_count = len(changes)
    await session.commit()
    await session.refresh(existing)
    log.info("thesis_generated", competitor=competitor.name, changes=len(changes))
    return existing
