"""Notion CRM sync — push enriched intelligence cards, idempotently.

Idempotency: every change carries its UUID into Notion as an "Argus ID" property.
Before creating a page we query for that id; if it already exists we adopt it
instead of creating a duplicate. So running the pipeline twice on the same change
never doubles up — even if the local crm_status were lost.

Resilience: a failed push marks the change ``crm_status=failed``; the next pipeline
run picks up all non-synced enriched changes and retries. Status is visible in the
``/changes`` feed, never silently dropped.

Sync is skipped entirely until a token + database id are configured, so the app
runs fine without Notion.
"""

from __future__ import annotations

import structlog
from notion_client import AsyncClient as NotionClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.change import Change, CrmStatus
from app.models.competitor import Competitor

log = structlog.get_logger()

_ARGUS_ID = "Argus ID"


def _truncate(text: str | None, limit: int = 1900) -> str:
    return (text or "")[:limit]


def _properties(change: Change, competitor: Competitor) -> dict:
    """Map a change to Notion page properties.

    Assumes a database with these properties (see README for the schema):
    Name (title), Competitor (rich_text), URL (url), Category (select),
    Impact Score (number), Summary (rich_text), Recommended Action (rich_text),
    Detected At (date), Argus ID (rich_text).
    """
    category = change.category.value if change.category else "other"
    title = f"{competitor.name} — {category}"
    return {
        "Name": {"title": [{"text": {"content": _truncate(title, 200)}}]},
        "Competitor": {"rich_text": [{"text": {"content": _truncate(competitor.name, 200)}}]},
        "URL": {"url": competitor.url},
        "Category": {"select": {"name": category}},
        "Impact Score": {"number": change.impact_score or 0},
        "Summary": {"rich_text": [{"text": {"content": _truncate(change.summary)}}]},
        "Recommended Action": {
            "rich_text": [{"text": {"content": _truncate(change.recommended_action)}}]
        },
        "Detected At": {"date": {"start": change.detected_at.isoformat()}},
        _ARGUS_ID: {"rich_text": [{"text": {"content": str(change.id)}}]},
    }


async def sync_change(
    client: NotionClient, database_id: str, change: Change, competitor: Competitor
) -> tuple[str, bool]:
    """Push one change. Returns (notion_page_id, created). Idempotent by Argus ID."""
    existing = await client.databases.query(
        database_id=database_id,
        filter={"property": _ARGUS_ID, "rich_text": {"equals": str(change.id)}},
    )
    results = existing.get("results", [])
    if results:
        return results[0]["id"], False

    page = await client.pages.create(
        parent={"database_id": database_id}, properties=_properties(change, competitor)
    )
    return page["id"], True


async def crm_sync_pending(session: AsyncSession) -> dict:
    """Push every enriched, not-yet-synced meaningful change to Notion."""
    stats = {"synced": 0, "crm_failed": 0}
    if not (settings.notion_token and settings.notion_database_id):
        return stats  # CRM not configured — skip silently

    client = NotionClient(auth=settings.notion_token)
    pending = (
        await session.execute(
            select(Change)
            .where(
                Change.is_meaningful.is_(True),
                Change.summary.is_not(None),
                Change.crm_status != CrmStatus.synced,
            )
            .order_by(Change.detected_at.asc())
        )
    ).scalars().all()

    for change in pending:
        competitor = await session.get(Competitor, change.competitor_id)
        try:
            page_id, _created = await sync_change(
                client, settings.notion_database_id, change, competitor
            )
        except Exception as exc:  # noqa: BLE001 — any Notion/transport error → retry next run
            change.crm_status = CrmStatus.failed
            stats["crm_failed"] += 1
            log.warning("crm_sync_failed", change_id=str(change.id), error=str(exc))
            continue
        change.crm_record_id = page_id
        change.dedupe_hash = str(change.id)
        change.crm_status = CrmStatus.synced
        stats["synced"] += 1

    await session.commit()
    return stats
