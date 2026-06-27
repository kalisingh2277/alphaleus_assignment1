"""Digest builder — grouping by competitor, ranking by impact, top-3 highlight."""

from app.services.digest import DigestItem, build_digest


def _item(competitor: str, score: int, category: str = "pricing") -> DigestItem:
    return DigestItem(
        competitor=competitor,
        url="https://example.com",
        category=category,
        impact_score=score,
        summary=f"{competitor} did something",
        recommended_action="Do X",
    )


def test_digest_ranks_and_groups():
    items = [_item("Acme", 3), _item("Acme", 9), _item("Beta", 7), _item("Gamma", 5)]
    subject, html, text = build_digest(items)

    assert "4 competitor update(s)" in subject
    for name in ("Acme", "Beta", "Gamma"):
        assert name in html
    # Highest-impact item appears (in the top section) before the lowest.
    assert text.index("[9/10]") < text.index("[3/10]")


def test_digest_highlights_exactly_top3():
    items = [_item(f"C{i}", i) for i in range(1, 7)]  # scores 1..6
    _subject, _html, text = build_digest(items)

    top_section = text.split("BY COMPETITOR")[0]
    for score in (6, 5, 4):
        assert f"[{score}/10]" in top_section
    assert "[3/10]" not in top_section  # 4th-highest is not in the top-3 highlight
