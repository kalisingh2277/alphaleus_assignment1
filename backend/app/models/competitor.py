"""The Competitor model — one monitored entity (a company + a page to watch)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.snapshot import PageSnapshot


class MonitorScope(str, enum.Enum):
    """Which part of the page we care about (mirrors the Chrome extension selector)."""

    full_page = "full_page"
    pricing = "pricing"
    careers = "careers"


class MonitorStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    error = "error"


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(2000))

    # native_enum=False stores the value as VARCHAR + CHECK, so adding a new
    # category later is a plain data change, not a fragile ALTER TYPE.
    monitor_scope: Mapped[MonitorScope] = mapped_column(
        Enum(MonitorScope, native_enum=False, length=20), default=MonitorScope.full_page
    )
    status: Mapped[MonitorStatus] = mapped_column(
        Enum(MonitorStatus, native_enum=False, length=20), default=MonitorStatus.active
    )
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=6)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    snapshots: Mapped[list[PageSnapshot]] = relationship(
        back_populates="competitor",
        cascade="all, delete-orphan",
        order_by="PageSnapshot.scraped_at.desc()",
    )
