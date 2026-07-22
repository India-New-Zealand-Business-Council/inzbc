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


def test_answer_query_does_not_match_on_jurisdiction_words_alone() -> None:
    # "education" has no corpus entry; matching on "india" alone would wrongly surface an
    # unrelated cross-sector entry instead of escalating to INZBC.
    assert answer_query("education in India") == []
    assert answer_query("new zealand") == []


def test_answer_query_returns_empty_for_blank_query() -> None:
    assert answer_query("") == []
    assert answer_query("   ") == []


def test_unconfirmed_entry_is_suppressed_from_member_answers() -> None:
    # docs/fta-source-corpus.md is explicit: do not cite the ~70% tariff-line figure in the
    # Explainer until it's confirmed against a primary source. A query that only matches that
    # unconfirmed entry must escalate to INZBC ([]), not surface it with a caveat.
    answers = answer_query("tariff line")
    assert answers == []
    assert all(entry.confirmed for entry in answer_query("dairy"))


def test_every_answer_carries_status_line_and_disclaimer_placeholder() -> None:
    for answer in answer_query("wine"):
        assert "not yet in force" in answer.status_line.lower()
        assert answer.disclaimer == DISCLAIMER_PLACEHOLDER
        assert answer.jurisdiction == "New Zealand-India"
