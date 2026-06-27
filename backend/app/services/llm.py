"""Local LLM impact scoring via Ollama.

Why Ollama and not an in-process GGUF runtime: Ollama does runtime CPU-feature
detection, so the same code runs on this dev box (AVX2, no AVX-512), on GitHub
Actions, and on the deploy host without instruction-set crashes. It is a separate
process, and only the enrichment path calls it, so the web host never loads a model.

Model: llama3.2 (Llama-3.2-3B-Instruct, Q4, ~2 GB). Measured ~20s/change on a
12th-gen i5 CPU — well under the 90s budget. Output is forced to a JSON schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import structlog
from ollama import AsyncClient

from app.core.config import settings

log = structlog.get_logger()


class LLMError(RuntimeError):
    """Raised when the model is unreachable or returns unusable output."""


@dataclass(slots=True)
class ImpactResult:
    summary: str
    impact_score: int
    impact_justification: str
    recommended_action: str
    category: str  # one of the six categories, as judged by the LLM


_CATEGORIES = ["pricing", "product", "hiring", "messaging", "leadership", "other"]


_SYSTEM = (
    "You are a competitive-intelligence analyst. You assess how much a competitor's "
    "change matters to the USER'S OWN business, not in the abstract. Score impact 1-10: "
    "10 = a direct threat to the user's core product or pricing; 1 = irrelevant to them. "
    "A change overlapping the user's core product, or undercutting their price, MUST score "
    "higher than a change in an unrelated area. Be specific and reference the user's business. "
    "Decide the category yourself from what changed."
)

# Ollama enforces this JSON schema on the output, so we always get parseable fields.
_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "impact_score": {"type": "integer"},
        "impact_justification": {"type": "string"},
        "recommended_action": {"type": "string"},
        "category": {"type": "string", "enum": _CATEGORIES},
    },
    "required": [
        "summary",
        "impact_score",
        "impact_justification",
        "recommended_action",
        "category",
    ],
}


def _user_prompt(profile: dict, competitor: str, detail: str) -> str:
    return (
        "OUR BUSINESS:\n"
        f"- Product: {profile.get('product') or '(unspecified)'}\n"
        f"- Customers: {profile.get('customers') or '(unspecified)'}\n"
        f"- Price point: {profile.get('price_point') or '(unspecified)'}\n\n"
        "COMPETITOR CHANGE:\n"
        f"- Competitor: {competitor}\n"
        f"- What changed: {detail}\n\n"
        "Return a one-paragraph summary of what changed and why it matters to OUR business, "
        "an integer impact_score 1-10, a one-sentence justification, a one-sentence "
        "recommended action for our business, and the single best category for this change "
        "(pricing, product, hiring, messaging, leadership, or other)."
    )


async def score_change(profile: dict, competitor: str, detail: str) -> ImpactResult:
    """Score one change with the LLM, relative to the user's business profile."""
    client = AsyncClient(host=settings.ollama_host)
    try:
        resp = await client.chat(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _user_prompt(profile, competitor, detail)},
            ],
            format=_SCHEMA,
            options={"temperature": settings.llm_temperature},
        )
    except Exception as exc:  # noqa: BLE001 — surface any client/transport error uniformly
        raise LLMError(f"Ollama call failed: {exc}") from exc

    try:
        data = json.loads(resp.message.content)
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        raise LLMError(f"LLM returned invalid JSON: {exc}") from exc

    try:
        score = max(1, min(10, int(data["impact_score"])))
    except (KeyError, ValueError, TypeError):
        score = 5  # neutral fallback rather than failing the whole change

    category = str(data.get("category", "other")).strip().lower()
    if category not in _CATEGORIES:
        category = "other"

    return ImpactResult(
        summary=str(data.get("summary", "")).strip(),
        impact_score=score,
        impact_justification=str(data.get("impact_justification", "")).strip(),
        recommended_action=str(data.get("recommended_action", "")).strip(),
        category=category,
    )
