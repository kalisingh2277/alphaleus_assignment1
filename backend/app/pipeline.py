"""The scheduled pipeline: scrape every active competitor and detect changes.

This is invoked three ways, all sharing the same code:
  * the in-process APScheduler (dev / simple deploys),
  * ``python -m app.pipeline`` from a GitHub Actions cron (the production path —
    keeps the heavy scrape+embed work off the always-on web host), and
  * the manual ``POST /api/v1/pipeline/run`` trigger (demos + tests).
"""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.competitor import Competitor, MonitorStatus
from app.services import scraper
from app.services.crm import crm_sync_pending
from app.services.enrich import enrich_pending
from app.services.ingest import ingest

log = structlog.get_logger()


async def run_pipeline() -> dict:
    """Scrape + detect across competitors, then LLM-score new changes."""
    stats = {
        "competitors": 0,
        "scraped": 0,
        "changes": 0,
        "meaningful": 0,
        "filtered": 0,
        "errors": 0,
        "scored": 0,
        "llm_errors": 0,
        "synced": 0,
        "crm_failed": 0,
    }
    async with SessionLocal() as session:
        competitors = (
            await session.execute(
                select(Competitor).where(Competitor.status != MonitorStatus.paused)
            )
        ).scalars().all()
        stats["competitors"] = len(competitors)

        for competitor in competitors:
            try:
                outcome = await ingest(session, competitor)
            except scraper.ScrapeError as exc:
                stats["errors"] += 1
                log.warning("scrape_failed", competitor=competitor.name, error=str(exc))
                continue

            stats["scraped"] += 1
            if outcome.change is not None:
                stats["changes"] += 1
                if outcome.change.is_meaningful:
                    stats["meaningful"] += 1
                else:
                    stats["filtered"] += 1

        # Score newly-detected meaningful changes (and retry any unscored ones).
        enrich_stats = await enrich_pending(session)
        stats["scored"] = enrich_stats["scored"]
        stats["llm_errors"] = enrich_stats["llm_errors"]

        # Push enriched cards to the CRM (and retry any previously-failed pushes).
        crm_stats = await crm_sync_pending(session)
        stats["synced"] = crm_stats["synced"]
        stats["crm_failed"] = crm_stats["crm_failed"]

    log.info("pipeline_run", **stats)
    return stats


async def _main() -> None:
    stats = await run_pipeline()
    print("pipeline run:", stats)


if __name__ == "__main__":
    asyncio.run(_main())
