"""Digest email — a grouped, ranked summary of recent intelligence.

Gathers meaningful, enriched changes since the last digest, groups them by
competitor, sorts by impact, highlights the top 3, and emails HTML + plain text
via SMTP. Suppressed entirely when nothing new was detected.

``build_digest`` is a pure function (no DB, no SMTP) so it is unit-tested directly.
"""

from __future__ import annotations

import asyncio
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_state import STATE_ID, AppState
from app.models.change import Change
from app.models.competitor import Competitor

log = structlog.get_logger()


@dataclass(slots=True)
class DigestItem:
    competitor: str
    url: str
    category: str
    impact_score: int
    summary: str
    recommended_action: str


def _impact_color(score: int) -> str:
    if score >= 8:
        return "#c0392b"  # red
    if score >= 5:
        return "#e67e22"  # amber
    return "#27ae60"  # green


def build_digest(items: list[DigestItem]) -> tuple[str, str, str]:
    """Return (subject, html, text). Assumes a non-empty item list."""
    ranked = sorted(items, key=lambda i: i.impact_score, reverse=True)
    top3 = ranked[:3]

    by_competitor: dict[str, list[DigestItem]] = {}
    for item in ranked:
        by_competitor.setdefault(item.competitor, []).append(item)

    subject = f"Argus digest — {len(items)} competitor update(s)"

    # --- HTML ---
    html = ["<div style='font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:640px'>"]
    html.append(f"<h2>Argus competitor intelligence</h2><p>{len(items)} new update(s).</p>")
    html.append("<h3>Top changes</h3>")
    for item in top3:
        color = _impact_color(item.impact_score)
        html.append(
            f"<div style='border-left:4px solid {color};padding:6px 12px;margin:8px 0'>"
            f"<b>{item.competitor}</b> "
            f"<span style='background:{color};color:#fff;border-radius:10px;padding:1px 8px;"
            f"font-size:12px'>{item.impact_score}/10 · {item.category}</span><br>"
            f"{item.summary}<br><i>Action:</i> {item.recommended_action}</div>"
        )
    html.append("<hr><h3>By competitor</h3>")
    for competitor, comp_items in by_competitor.items():
        html.append(f"<h4>{competitor}</h4><ul>")
        for item in comp_items:
            color = _impact_color(item.impact_score)
            html.append(
                f"<li><span style='color:{color};font-weight:bold'>[{item.impact_score}/10]</span> "
                f"({item.category}) {item.summary}</li>"
            )
        html.append("</ul>")
    html.append("</div>")

    # --- plain text ---
    text = [f"Argus digest — {len(items)} new update(s)", "", "TOP CHANGES:"]
    for item in top3:
        text.append(
            f"  [{item.impact_score}/10] {item.competitor} ({item.category}): {item.summary}"
        )
        text.append(f"      Action: {item.recommended_action}")
    text.append("")
    text.append("BY COMPETITOR:")
    for competitor, comp_items in by_competitor.items():
        text.append(f"  {competitor}:")
        for item in comp_items:
            text.append(f"    [{item.impact_score}/10] ({item.category}) {item.summary}")

    return subject, "\n".join(html), "\n".join(text)


def _smtp_configured() -> bool:
    return all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.digest_to])


def _send_email(subject: str, html: str, text: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.digest_from or settings.smtp_user
    msg["To"] = settings.digest_to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def _get_state(session: AsyncSession) -> AppState:
    state = await session.get(AppState, STATE_ID)
    if state is None:
        state = AppState(id=STATE_ID)
        session.add(state)
        await session.commit()
        await session.refresh(state)
    return state


async def send_digest(session: AsyncSession) -> dict:
    """Build + send a digest of changes since the last one. Suppresses if empty."""
    if not _smtp_configured():
        return {"sent": False, "reason": "smtp_not_configured", "count": 0}

    state = await _get_state(session)
    stmt = select(Change).where(Change.is_meaningful.is_(True), Change.summary.is_not(None))
    if state.last_digest_sent_at is not None:
        stmt = stmt.where(Change.detected_at > state.last_digest_sent_at)
    changes = (await session.execute(stmt)).scalars().all()
    if not changes:
        return {"sent": False, "reason": "no_new_changes", "count": 0}

    competitors = {
        c.id: c for c in (await session.execute(select(Competitor))).scalars().all()
    }
    items: list[DigestItem] = []
    for c in changes:
        comp = competitors.get(c.competitor_id)
        items.append(
            DigestItem(
                competitor=comp.name if comp else "Unknown",
                url=comp.url if comp else "",
                category=c.category.value if c.category else "other",
                impact_score=c.impact_score or 0,
                summary=c.summary or "",
                recommended_action=c.recommended_action or "",
            )
        )
    subject, html, text = build_digest(items)
    await asyncio.to_thread(_send_email, subject, html, text)

    state.last_digest_sent_at = datetime.now(UTC)
    await session.commit()
    log.info("digest_sent", count=len(items))
    return {"sent": True, "count": len(items)}


async def _main() -> None:
    from app.core.database import SessionLocal, init_db

    await init_db()
    async with SessionLocal() as session:
        print("digest:", await send_digest(session))


if __name__ == "__main__":
    asyncio.run(_main())
