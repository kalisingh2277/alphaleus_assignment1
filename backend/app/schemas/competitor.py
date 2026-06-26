"""Pydantic request/response models — the public shape of the API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.change import ChangeCategory, CrmStatus
from app.models.competitor import MonitorScope, MonitorStatus


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Acme Corp"])
    url: HttpUrl = Field(examples=["https://acme.example.com/pricing"])
    monitor_scope: MonitorScope = MonitorScope.full_page


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    url: str
    monitor_scope: MonitorScope
    status: MonitorStatus
    check_interval_hours: int
    created_at: datetime
    last_checked_at: datetime | None
    last_error: str | None


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competitor_id: uuid.UUID
    content_hash: str
    char_count: int
    http_status: int | None
    extraction_method: str
    scraped_at: datetime


class ChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competitor_id: uuid.UUID
    from_snapshot_id: uuid.UUID | None
    to_snapshot_id: uuid.UUID
    similarity: float | None
    is_meaningful: bool
    category: ChangeCategory | None
    structured_diff: dict | None
    summary: str | None
    impact_score: int | None
    recommended_action: str | None
    crm_status: CrmStatus
    detected_at: datetime


class PipelineRunResult(BaseModel):
    """Summary returned by a pipeline run (manual trigger or scheduled)."""

    competitors: int
    scraped: int
    changes: int
    meaningful: int
    filtered: int
    errors: int
    scored: int
    llm_errors: int
    synced: int
    crm_failed: int


class ScrapeResult(BaseModel):
    """Returned by the manual 'scrape now' endpoint.

    ``changed`` = content hash differs from the previous snapshot.
    ``is_meaningful`` = semantic distance exceeded the threshold (noise filtered out).
    """

    snapshot: SnapshotOut
    is_first: bool
    changed: bool
    is_meaningful: bool
    similarity: float | None
    category: ChangeCategory | None
    structured_diff: dict | None
    preview: str
