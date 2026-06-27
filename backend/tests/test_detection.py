"""Detection layer: meaningful-vs-cosmetic on representative page fixtures.

Offline (no DB, no network beyond the cached embedding model). These are the
assignment's "5 test URLs covering different change types" as deterministic
fixtures: pricing / product / hiring meaningful changes, plus cookie-banner and
date-reword cosmetic noise. They guard the two filter layers (boilerplate strip
+ semantic threshold) and the structured signal that catches pricing.
"""

import pytest

from app.core.config import settings
from app.services import classifier, embeddings, structured
from app.services.scraper import extract_main_text

_NAV = "<nav>Home Products Pricing Careers About</nav>"


def _page(body: str, foot: str = "<footer>(c) 2024 Acme Inc.</footer>",
          cookie: str = "<div id='cookie'>We use cookies. Accept?</div>") -> str:
    return f"<html><body>{_NAV}{cookie}<main>{body}</main>{foot}</body></html>"


def _decide(old_html: str, new_html: str) -> dict:
    """Replicate the ingest decision on two raw HTML versions."""
    old_text, new_text = extract_main_text(old_html), extract_main_text(new_html)
    if old_text == new_text:  # boilerplate strip collapsed the change
        return {"meaningful": False, "category": None, "delta": None}

    cosine = embeddings.cosine_similarity(embeddings.embed(old_text), embeddings.embed(new_text))
    sdiff = structured.diff_fields(
        structured.extract_fields(old_text), structured.extract_fields(new_text)
    )
    added = classifier.changed_text(old_text, new_text)
    removed = classifier.changed_text(new_text, old_text)
    substantial_new = (len(added) - len(removed)) >= settings.min_new_content_chars
    meaningful = (
        cosine < settings.semantic_change_threshold or sdiff is not None or substantial_new
    )
    if not meaningful:
        return {"meaningful": False, "category": None, "delta": None}
    if sdiff and "prices" in sdiff:
        return {"meaningful": True, "category": "pricing", "delta": sdiff["prices"].get("delta")}
    category = classifier.classify(old_text, new_text).value
    return {"meaningful": True, "category": category, "delta": None}


_PRICING = (
    _page("<h1>Pricing</h1><p>Starter is free. Pro plan is $99 per month for unlimited seats.</p>"),
    _page("<h1>Pricing</h1><p>Starter is free. Pro plan is $79 per month for unlimited seats.</p>"),
    True, "pricing",
)
_PRODUCT = (
    _page("<h1>Product</h1><p>Acme helps teams manage projects with boards and reporting.</p>"),
    _page("<h1>Product</h1><p>Acme helps teams manage projects with boards and reporting. "
          "New: an AI Assistant that auto-summarizes standups is now available.</p>"),
    True, "product",
)
_HIRING = (
    _page("<h1>Careers</h1><p>Open roles: Account Executive in New York.</p>"),
    _page("<h1>Careers</h1><p>Open roles: Account Executive in New York. Senior Machine "
          "Learning Engineer and Applied AI Researcher in London.</p>"),
    True, "hiring",
)
_COOKIE_NOISE = (
    _page("<h1>About</h1><p>Acme was founded in 2015 to make work simpler.</p>",
          cookie="<div id='cookie'>We use cookies. Accept?</div>"),
    _page("<h1>About</h1><p>Acme was founded in 2015 to make work simpler.</p>",
          foot="<footer>(c) 2025 Acme Inc. Updated privacy policy.</footer>",
          cookie="<div id='cookie'>This site uses cookies for analytics.</div>"),
    False, None,
)
_DATE_NOISE = (
    _page("<h1>Blog</h1><p>Annual report. Last updated June 2024. "
          "We served customers worldwide.</p>"),
    _page("<h1>Blog</h1><p>Annual report. Last updated July 2024. "
          "We served customers worldwide.</p>"),
    False, None,
)


@pytest.mark.parametrize(
    "old_html,new_html,expect_meaningful,expect_category",
    [_PRICING, _PRODUCT, _HIRING, _COOKIE_NOISE, _DATE_NOISE],
    ids=["pricing", "product", "hiring", "cookie_noise", "date_noise"],
)
def test_meaningful_vs_cosmetic(old_html, new_html, expect_meaningful, expect_category):
    result = _decide(old_html, new_html)
    assert result["meaningful"] is expect_meaningful
    if expect_meaningful:
        assert result["category"] == expect_category


def test_pricing_change_yields_delta():
    """The structured signal must catch the price drop embeddings miss, with a delta."""
    result = _decide(_PRICING[0], _PRICING[1])
    assert result["meaningful"] is True
    assert result["category"] == "pricing"
    assert result["delta"] == "$99 → $79 (-20%)"
