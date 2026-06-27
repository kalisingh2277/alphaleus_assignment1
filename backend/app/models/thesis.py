"""CompetitorThesis — the cached strategic synthesis across a competitor's changes.

Generating it is an LLM call, so we cache one row per competitor and only
regenerate when the number of meaningful changes has grown.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompetitorThesis(Base):
    __tablename__ = "competitor_thesis"

    competitor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"), primary_key=True
    )
    headline: Mapped[str] = mapped_column(String(200))
    narrative: Mapped[str] = mapped_column(Text)
    recommended_focus: Mapped[str] = mapped_column(Text)
    change_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
