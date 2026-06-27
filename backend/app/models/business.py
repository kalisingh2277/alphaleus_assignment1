"""BusinessProfile — the user's own-business context for LLM impact scoring.

A single-row (singleton) table: there is one profile per deployment, captured
during onboarding. The LLM scores every change relative to this, so impact is
specific to the user's product/customers/price rather than generic.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SINGLETON_ID = 1


class BusinessProfile(Base):
    __tablename__ = "business_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=SINGLETON_ID)
    product: Mapped[str] = mapped_column(Text, default="")
    customers: Mapped[str] = mapped_column(Text, default="")
    price_point: Mapped[str] = mapped_column(String(200), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
