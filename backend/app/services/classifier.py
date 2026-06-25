"""Model-based change classifier (not a ruleset).

The assignment requires a *model*, not keyword rules. We isolate the *new
sentences* between two snapshots, embed them, and pick the nearest category
centroid — a zero-shot nearest-centroid classifier on the same fastembed model.
No extra dependency, CPU-bound, and it classifies what actually changed.

Two design choices make it stable: (1) sentence-level diffing isolates the new
content instead of diluting it with the surrounding paragraph; (2) each category
is anchored by several natural example sentences whose embeddings are averaged
into a centroid, which generalises far better than a single keyword bag.

On Day 3 the LLM independently emits a category in its structured output, giving
a cheap cross-check; this classifier is the fast first pass.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.core.config import settings
from app.models.change import ChangeCategory
from app.services import embeddings

# A handful of natural phrasings per category — averaged into a centroid.
_ANCHOR_EXAMPLES: dict[ChangeCategory, list[str]] = {
    ChangeCategory.pricing: [
        "Our pricing plans and monthly subscription cost.",
        "The Pro plan now costs a different amount per month.",
        "Updated pricing, billing, discounts, and per-seat fees.",
    ],
    ChangeCategory.product: [
        "We launched a new product feature.",
        "A new capability or integration is now available to customers.",
        "Product update: improvements and new functionality shipped.",
    ],
    ChangeCategory.hiring: [
        "We are hiring for new open job positions.",
        "New careers and engineering roles on our team.",
        "Job opening: apply now to join our growing team.",
    ],
    ChangeCategory.messaging: [
        "We refreshed our brand tagline and positioning.",
        "A new homepage headline and value proposition.",
        "Our company mission and marketing messaging.",
    ],
    ChangeCategory.leadership: [
        "We appointed a new CEO or executive.",
        "Leadership change: a new CTO joins the leadership team.",
        "A founder is stepping down and the board is changing.",
    ],
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


@lru_cache(maxsize=1)
def _anchor_centroids() -> dict[ChangeCategory, list[float]]:
    centroids: dict[ChangeCategory, list[float]] = {}
    for category, examples in _ANCHOR_EXAMPLES.items():
        vectors = [embeddings.embed(example) for example in examples]
        dim = len(vectors[0])
        centroids[category] = [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]
    return centroids


def _segments(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def changed_text(old_text: str, new_text: str) -> str:
    """Return the sentences present in ``new_text`` but not in ``old_text``."""
    old_segments = set(_segments(old_text))
    added = [s for s in _segments(new_text) if s not in old_segments]
    return " ".join(added).strip()


def classify(old_text: str, new_text: str) -> ChangeCategory:
    """Classify the change into one of the six categories."""
    snippet = changed_text(old_text, new_text) or new_text
    vector = embeddings.embed(snippet[: embeddings.MAX_CHARS])
    scores = {
        category: embeddings.cosine_similarity(vector, centroid)
        for category, centroid in _anchor_centroids().items()
    }
    best_category, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < settings.classifier_min_confidence:
        return ChangeCategory.other
    return best_category
