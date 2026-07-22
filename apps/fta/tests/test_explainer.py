from __future__ import annotations

from apps.fta.explainer import DISCLAIMER_PLACEHOLDER, answer_query


def test_answer_query_matches_a_specific_product() -> None:
    answers = answer_query("wool")
    assert len(answers) == 1
    assert answers[0].topic == "Wool"
    assert answers[0].confirmed is True


def test_answer_query_matches_a_sector_with_multiple_entries() -> None:
    answers = answer_query("dairy")
    topics = {a.topic for a in answers}
    assert "Dairy - milk, cheese, butter" in topics
    assert "Dairy - bulk infant formula and other dairy-based food preparations" in topics
    assert "Dairy - peptones" in topics
    assert "Dairy - albumins" in topics


def test_answer_query_distinguishes_milk_from_infant_formula() -> None:
    answers = answer_query("infant formula")
    topics = {a.topic for a in answers}
    assert "Dairy - bulk infant formula and other dairy-based food preparations" in topics
    assert "Dairy - milk, cheese, butter" not in topics


def test_answer_query_returns_empty_for_no_match() -> None:
    assert answer_query("semiconductor export controls") == []


def test_answer_query_returns_empty_for_stopwords_only() -> None:
    assert answer_query("the and of") == []


def test_answer_query_returns_empty_for_blank_query() -> None:
    assert answer_query("") == []
    assert answer_query("   ") == []


def test_unconfirmed_entry_is_never_presented_as_confirmed() -> None:
    answers = answer_query("tariff line")
    unconfirmed = [a for a in answers if not a.confirmed]
    assert unconfirmed
    for answer in unconfirmed:
        assert "not yet confirmed" in answer.next_step


def test_every_answer_carries_status_line_and_disclaimer_placeholder() -> None:
    for answer in answer_query("wine"):
        assert "not yet in force" in answer.status_line.lower()
        assert answer.disclaimer == DISCLAIMER_PLACEHOLDER
        assert answer.jurisdiction == "New Zealand-India"
