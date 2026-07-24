from __future__ import annotations

from apps.fta.explainer import DISCLAIMER, NO_MATCH_CONFIDENCE, answer_query
from apps.fta.standards import AI_INFORMATION_STANDARD, Confidence


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


def test_every_answer_carries_status_line_and_approved_disclaimer() -> None:
    for answer in answer_query("wine"):
        assert "not yet in force" in answer.status_line.lower()
        assert answer.disclaimer == DISCLAIMER == AI_INFORMATION_STANDARD
        assert "[[" not in answer.disclaimer  # approved wording, no placeholder residue
        assert "indicate this rather than speculate" in answer.disclaimer
        assert answer.jurisdiction == "New Zealand-India"


def test_confirmed_tier1_answers_rate_high_confidence() -> None:
    # Every corpus entry that reaches a member today cites a Tier 1 (MFAT) source, so the
    # Information Confidence Standard rates them High, with the standard's meaning text.
    answers = answer_query("dairy")
    assert answers
    for answer in answers:
        assert answer.confidence is Confidence.HIGH
        assert answer.confidence_meaning == Confidence.HIGH.meaning
        assert "official government or treaty sources" in answer.confidence_meaning


def test_no_match_confidence_is_action_required() -> None:
    # The [] escalate-to-INZBC path is surfaced to users as Action Required per the standard.
    assert NO_MATCH_CONFIDENCE is Confidence.ACTION_REQUIRED
    assert "contacting the relevant government agency" in NO_MATCH_CONFIDENCE.meaning
