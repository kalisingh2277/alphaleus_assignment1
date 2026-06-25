"""Scraping + clean-text extraction.

Day 1 handles static HTML. We deliberately use trafilatura for extraction rather
than dumping raw HTML: it pulls out the *main content* and discards nav bars,
cookie banners, footers, and ad blocks. That boilerplate removal is the first
line of defence against cosmetic noise — the thing the assignment explicitly
says string-diffing fails at. Day 2 adds a headless path for JS-rendered pages.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import httpx
import trafilatura

from app.core.config import settings

_DEFAULT_HEADERS = {
    "User-Agent": settings.scraper_user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


class ScrapeError(RuntimeError):
    """Raised when a page cannot be fetched."""


@dataclass(slots=True)
class ScrapeOutput:
    clean_text: str
    content_hash: str
    http_status: int
    extraction_method: str


async def fetch_html(url: str) -> tuple[int, str]:
    """Fetch a URL with browser-like headers. Follows redirects."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.request_timeout_seconds,
            headers=_DEFAULT_HEADERS,
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:  # network/DNS/timeout
        raise ScrapeError(f"Could not fetch {url}: {exc}") from exc

    if resp.status_code >= 400:
        raise ScrapeError(f"{url} returned HTTP {resp.status_code}")
    return resp.status_code, resp.text


def extract_main_text(html: str, url: str | None = None) -> str:
    """Extract the readable main content, stripping boilerplate."""
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    if extracted:
        return extracted.strip()
    return _fallback_strip(html)


def _fallback_strip(html: str) -> str:
    """Crude tag-strip for pages trafilatura can't parse (keeps Day 1 robust)."""
    no_scripts = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", no_scripts)
    return _WS_RE.sub(" ", text).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def scrape(url: str) -> ScrapeOutput:
    """Fetch + extract a static page into a normalised ScrapeOutput."""
    status, html = await fetch_html(url)
    text = extract_main_text(html, url)
    return ScrapeOutput(
        clean_text=text,
        content_hash=content_hash(text),
        http_status=status,
        extraction_method="static",
    )
