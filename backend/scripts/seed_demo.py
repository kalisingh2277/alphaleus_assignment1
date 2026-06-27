"""Seed realistic demo data: competitors with genuinely-detected, scored changes.

This runs the REAL ingest path on scripted, cumulative page versions, so every
change is actually detected (semantic + structured) and classified — nothing is
faked — then LLM-scored. Intended for a fresh database.

Nimbus has a three-change storyline (price cut -> AI hiring -> AI feature) that
sets up the cross-change "competitor thesis" view.

    docker compose up -d db
    cd backend && uv run python scripts/seed_demo.py
"""

import asyncio

from app.core.database import SessionLocal, init_db
from app.models.business import SINGLETON_ID, BusinessProfile
from app.models.competitor import Competitor
from app.services import scraper
from app.services.enrich import enrich_pending
from app.services.ingest import ingest
from app.services.scraper import ScrapeOutput, content_hash

PROFILE = dict(
    product="A project management SaaS for small remote teams (boards, timelines, reporting)",
    customers="Startups and small businesses, 5-50 employees",
    price_point="$59/month Pro plan",
)


def _scrape_returning(text: str):
    async def fake(_url: str) -> ScrapeOutput:
        return ScrapeOutput(
            clean_text=text, content_hash=content_hash(text), http_status=200,
            extraction_method="static",
        )
    return fake


# Each competitor: cumulative page versions. Each new version introduces ONE change.
# After the baseline, changes are append-only (except the price, which is modified
# in place) so the diff is clean and the right signal fires.
_NIMBUS_BASE = (
    "Nimbus — project management for modern software teams. Plan your work with boards, "
    "sprints, and timelines in one place. Pricing: the Free plan is for individuals. The Pro "
    "plan is {price} per month for unlimited projects and members. The Enterprise plan is "
    "custom. Thousands of engineering teams rely on Nimbus to ship faster."
)
_NIMBUS_HIRING = (
    " Careers: Nimbus is now hiring a Senior Machine Learning Engineer and an Applied AI "
    "Researcher in London. We have several open engineering roles as we grow our team this year. "
    "View all open positions on our careers page."
)
_NIMBUS_PRODUCT = (
    " New feature: Nimbus AI now automatically writes your daily standup summaries and "
    "re-prioritizes your backlog for you. Nimbus AI is available to all Pro customers today."
)
_NIMBUS = [
    _NIMBUS_BASE.format(price="$90"),                                      # baseline
    _NIMBUS_BASE.format(price="$69"),                                      # 1) price cut $90->$69
    _NIMBUS_BASE.format(price="$69") + _NIMBUS_HIRING,                     # 2) AI hiring
    _NIMBUS_BASE.format(price="$69") + _NIMBUS_HIRING + _NIMBUS_PRODUCT,   # 3) AI product launch
]

_GANTTPRO_BASE = (
    "GanttPro — visual project timelines and Gantt charts for project managers. Build plans, "
    "track milestones, and manage team resources. Pricing: the Team plan is $49 per month and "
    "the Business plan is $99 per month. GanttPro is used by construction, marketing, and "
    "software teams worldwide."
)
_GANTTPRO = [
    _GANTTPRO_BASE,
    # new cheaper Starter tier at $29 (adds a price -> structured pricing signal)
    _GANTTPRO_BASE + " Update: GanttPro has launched a new Starter plan at just $29 per month "
    "for small teams getting started with project planning.",
]

_BRIGHTDESK_BASE = (
    "BrightDesk — customer support and helpdesk software. Manage tickets, live chat, and a "
    "self-serve knowledge base from one shared inbox. Pricing starts at $25 per agent per "
    "month. BrightDesk helps support teams reply faster and keep customers happy."
)
_BRIGHTDESK = [
    _BRIGHTDESK_BASE,
    # leadership change (adjacent market -> should score lower)
    _BRIGHTDESK_BASE + " Company news: BrightDesk has appointed Maria Chen as its new Chief "
    "Executive Officer. Maria joins from a leading SaaS company to lead the next phase of growth.",
]

_COMPETITORS = [
    ("Nimbus", "https://nimbus.example.com/pricing", _NIMBUS),
    ("GanttPro", "https://ganttpro.example.com/pricing", _GANTTPRO),
    ("BrightDesk", "https://brightdesk.example.com", _BRIGHTDESK),
]


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        if await session.get(BusinessProfile, SINGLETON_ID) is None:
            session.add(BusinessProfile(id=SINGLETON_ID, **PROFILE))
            await session.commit()

        for name, url, versions in _COMPETITORS:
            competitor = Competitor(name=name, url=url)
            session.add(competitor)
            await session.commit()
            await session.refresh(competitor)
            for version in versions:
                scraper.scrape = _scrape_returning(version)
                out = await ingest(session, competitor)
                if out.change and out.change.is_meaningful:
                    print(f"  {name}: detected {out.change.category.value}")
                elif out.change:
                    print(f"  {name}: FILTERED (not meaningful, sim={out.change.similarity:.3f})")

        print("\nEnriching with the LLM (this calls Ollama, ~20s each)...")
        print("enriched:", await enrich_pending(session))


if __name__ == "__main__":
    asyncio.run(main())
