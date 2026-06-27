"""PageSnapshot — one scraped version of a competitor's page at a point in time.

The ``embedding`` column is populated on Day 2 (semantic change detection). It is
defined now, nullable, so adding embeddings later needs no schema migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.competitor import Competitor

# fastembed's default (BAAI/bge-small-en-v1.5) emits 384-dim vectors.
EMBEDDING_DIM = 384


class PageSnapshot(Base):
    __tablename__ = "page_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), index=True
    )

    clean_text: Mapped[str] = mapped_column(Text)
    # sha256 of clean_text — a cheap exact-match check that short-circuits the
    # expensive semantic comparison when nothing changed at all.
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(20), default="static")  # static | js

    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    # Typed snapshot of high-value fields (prices today; extensible). Powers the
    # field-level diff that catches changes embeddings miss.
    structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitor: Mapped[Competitor] = relationship(back_populates="snapshots")
