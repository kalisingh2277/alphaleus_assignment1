"""Change — a detected difference between two consecutive snapshots.

We record *every* difference (hash changed), meaningful or not, so the UI can
later show "we filtered N cosmetic changes" — turning the noise filter into a
visible trust signal. The Day-3 LLM fields (summary, impact, action, CRM status)
are defined now, nullable, because Day 1/2 use create_all (no migrations yet) and
this lets Day 3 populate them without altering the table.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.competitor import Competitor


class ChangeCategory(str, enum.Enum):
    pricing = "pricing"
    product = "product"
    hiring = "hiring"
    messaging = "messaging"
    leadership = "leadership"
    other = "other"


class CrmStatus(str, enum.Enum):
    pending = "pending"  # not yet pushed
    synced = "synced"
    failed = "failed"  # queued for retry on next run


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), index=True
    )
    from_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("page_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    to_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("page_snapshots.id", ondelete="CASCADE")
    )

    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_meaningful: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    category: Mapped[ChangeCategory | None] = mapped_column(
        Enum(ChangeCategory, native_enum=False, length=20), nullable=True
    )
    # Field-level diff (e.g. {"prices": {"delta": "$99 → $79 (-20%)", ...}}) — the
    # precise, human-readable record of what actually changed.
    structured_diff: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # --- Day 3: LLM impact scoring (nullable until populated) ---
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Day 3: CRM sync state ---
    crm_status: Mapped[CrmStatus] = mapped_column(
        Enum(CrmStatus, native_enum=False, length=20), default=CrmStatus.pending, index=True
    )
    crm_record_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # sha256 of the change's identity — the idempotency key for CRM upserts.
    dedupe_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    competitor: Mapped[Competitor] = relationship()
