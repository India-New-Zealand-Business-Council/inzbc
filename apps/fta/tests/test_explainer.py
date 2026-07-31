from __future__ import annotations

from apps.fta.explainer import (
    DISCLAIMER,
    NO_MATCH_CONFIDENCE,
    ExplainerAnswer,
    answer_query,
    no_match,
)
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


def test_answer_query_ranks_a_multi_term_match_above_a_sector_only_match() -> None:
    # "peptones dairy" shares two keywords with "Dairy - peptones" (topic + sector) but only one
    # ("dairy", the sector) with the other three Dairy entries. This specific query is chosen
    # because "Dairy - peptones" is *not* first in CORPUS's own definition order (milk/cheese/
    # butter is) - a test that only ever checks the one case where ranked and insertion order
    # happen to coincide would not catch ranking being silently disabled, which is exactly what
    # happened here first: this test originally used "dairy milk", whose correct order matches
    # CORPUS's insertion order regardless of whether ranking runs at all.
    answers = answer_query("peptones dairy")
    assert answers[0].topic == "Dairy - peptones"
    assert {a.topic for a in answers} == {
        "Dairy - milk, cheese, butter",
        "Dairy - bulk infant formula and other dairy-based food preparations",
        "Dairy - peptones",
        "Dairy - albumins",
    }


def test_answer_query_gives_entries_with_equal_relevance_a_stable_order() -> None:
    # Plain "dairy" scores all four Dairy entries equally (sector-only match, same weight) - the
    # tiebreak must be deterministic (entry id), not whatever order a dict/set iteration happens
    # to produce, so the same query always returns the same order.
    first = [a.topic for a in answer_query("dairy")]
    second = [a.topic for a in answer_query("dairy")]
    assert first == second


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


def test_no_match_carries_escalation_not_an_answer() -> None:
    result = no_match("semiconductor export controls")
    assert result.query == "semiconductor export controls"
    assert result.confidence is Confidence.ACTION_REQUIRED
    assert result.confidence_meaning == Confidence.ACTION_REQUIRED.meaning
    assert result.message and result.next_step and result.escalation_path
    assert "INZBC" in result.escalation_path


def test_no_match_is_structurally_not_an_answer() -> None:
    # The safety property: a renderer must not be able to feed a no-match through the
    # sourced-answer path and present escalation guidance as an FTA finding. Enforced by the
    # type carrying none of the evidence fields, not by naming.
    result = no_match("semiconductor export controls")
    assert not isinstance(result, ExplainerAnswer)
    for evidence_field in ("topic", "sector", "treatment", "citation", "verified_at", "confirmed"):
        assert not hasattr(result, evidence_field), (
            f"NoMatch must not expose {evidence_field!r} - it is what makes a response look sourced"
        )


def test_no_match_carries_status_line_and_approved_disclaimer() -> None:
    result = no_match("anything unmatched")
    assert "not yet in force" in result.status_line.lower()
    assert result.disclaimer == DISCLAIMER == AI_INFORMATION_STANDARD
    assert "[[" not in result.disclaimer
    assert result.jurisdiction == "New Zealand-India"


def test_no_match_never_asserts_a_tariff_outcome() -> None:
    # Guards against someone later writing reassuring copy that reads like a finding.
    result = no_match("semiconductor export controls")
    prose = f"{result.message} {result.next_step} {result.escalation_path}".lower()
    for claim in ("tariff eliminated", "duty-free", "duty free", "%", "no tariff"):
        assert claim not in prose, f"no-match copy must not assert an outcome: found {claim!r}"


def test_empty_and_stopword_queries_route_to_no_match() -> None:
    for query in ("", "   ", "the and of"):
        assert answer_query(query) == []
        assert no_match(query).confidence is Confidence.ACTION_REQUIRED
