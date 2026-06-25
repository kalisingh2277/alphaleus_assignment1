"""In-process scheduler (APScheduler).

Off by default (``ENABLE_SCHEDULER=false``): tests and dev shouldn't fire
background scrapes, and in production the pipeline runs via GitHub Actions cron
to keep the heavy work off the web host. This exists for simple single-service
deploys and local demos.
"""

from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.pipeline import run_pipeline

log = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_pipeline,
        IntervalTrigger(hours=settings.scrape_interval_hours),
        id="scrape_all",
        max_instances=1,  # never overlap runs (memory safety)
        coalesce=True,  # if we missed ticks, run once, not N times
    )
    _scheduler.start()
    log.info("scheduler_started", interval_hours=settings.scrape_interval_hours)


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
