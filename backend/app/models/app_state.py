"""AppState — a single-row table for app-wide cursors.

Holds 'last digest sent' (so a digest only covers changes since the previous one)
and 'last feed viewed' (so the extension badge can count unread cards). Kept as a
new table rather than per-row flags so we add no columns to existing tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

STATE_ID = 1


class AppState(Base):
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=STATE_ID)
    last_digest_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_feed_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
