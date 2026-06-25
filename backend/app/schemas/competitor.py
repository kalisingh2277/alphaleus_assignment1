"""Pydantic request/response models — the public shape of the API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

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


class ScrapeResult(BaseModel):
    """Returned by the manual 'scrape now' endpoint.

    ``changed`` is a Day-1 exact-hash comparison vs the previous snapshot.
    Day 2 replaces this with semantic distance + noise filtering.
    """

    snapshot: SnapshotOut
    is_first: bool
    changed: bool
    preview: str
