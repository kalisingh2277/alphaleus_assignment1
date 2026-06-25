"""Structured field extraction + field-level diffing.

Full-page embeddings are blind to small-but-critical edits: a 20% price drop
scores ~0.99 cosine (verified empirically). So alongside the semantic signal we
extract a *typed snapshot* of high-value fields and diff them directly. A changed
tracked field forces a "meaningful" change even when embeddings smooth it over —
and yields a precise card ("$99 → $79 (-20%)") instead of a vague paragraph.

Day 2 tracks prices (the flagship case). The structure is extensible to headcount,
plan names, and exec names, which the Day-3 LLM also extracts.
"""

from __future__ import annotations

import re

# Currency amount: $99, £1,299, €49.99, $79  (years like 2024 are ignored — no symbol)
_PRICE_RE = re.compile(r"([$£€])\s?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)")


def extract_fields(text: str) -> dict:
    """Extract the typed snapshot for a page's clean text."""
    prices: list[str] = []
    seen: set[str] = set()
    for currency, amount in _PRICE_RE.findall(text or ""):
        token = f"{currency}{amount}"
        if token not in seen:
            seen.add(token)
            prices.append(token)
    return {"prices": prices}


def _to_float(token: str) -> float | None:
    match = re.search(r"\d[\d,]*(?:\.\d+)?", token)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def diff_fields(old: dict, new: dict) -> dict | None:
    """Return a structured diff if a tracked field changed, else None."""
    old_prices = old.get("prices", []) or []
    new_prices = new.get("prices", []) or []
    if set(old_prices) == set(new_prices):
        return None

    added = [p for p in new_prices if p not in set(old_prices)]
    removed = [p for p in old_prices if p not in set(new_prices)]
    entry: dict = {"before": old_prices, "after": new_prices, "added": added, "removed": removed}

    # When exactly one price was swapped, render a human delta for the UI card.
    if len(added) == 1 and len(removed) == 1:
        new_val, old_val = _to_float(added[0]), _to_float(removed[0])
        if new_val is not None and old_val not in (None, 0):
            pct = round((new_val - old_val) / old_val * 100)
            entry["delta"] = f"{removed[0]} → {added[0]} ({pct:+d}%)"

    return {"prices": entry}
