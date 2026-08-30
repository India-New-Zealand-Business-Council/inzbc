from __future__ import annotations

from dataclasses import fields
from datetime import date

from apps.fta import explainer
from apps.fta.corpus import TariffOutcome, TradeDirection
from apps.fta.explainer import (
    DISCLAIMER,
    NO_MATCH_CONFIDENCE,
    Depth,
    ExplainerAnswer,
    InternalAnswer,
    MemberAnswer,
    PublicAnswer,
    answer_query,
    answer_query_at_depth,
    no_match,
)
from apps.fta.standards import AI_INFORMATION_STANDARD, Confidence


def _entry(entry_id: str, topic: str) -> TariffOutcome:
    """A confirmed entry that scores only on its sector, so a set of them ties exactly."""
    return TariffOutcome(
        id=entry_id,
        topic=topic,
        sector="Wool",
        treatment="Tariff eliminated on entry into force.",
        confirmed=True,
        citation="MFAT National Interest Analysis",
        verified_at=date(2026, 7, 20),
        notes=None,
        source_tier=1,
    )


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


def test_answer_query_gives_entries_with_equal_relevance_a_stable_order(monkeypatch) -> None:
    """Equal-scoring entries come back in entry-id order, not corpus order.

    Calling the function twice and comparing cannot show this. `answer_query` is pure and the
    corpus is a module-level list, so two calls agree whatever the tiebreak is, and the assertion
    holds even with no tiebreak at all. Deleting `entry.id` from the sort key left the whole file
    passing.

    The property only has teeth when corpus order and id order disagree, so the corpus here is
    built deliberately backwards. Without the id tiebreak the result follows insertion order and
    this fails.
    """
    reversed_corpus = [
        _entry("FTA-902", "Wool - carpet grades"),
        _entry("FTA-901", "Wool - carded"),
        _entry("FTA-900", "Wool - greasy"),
    ]
    monkeypatch.setattr(explainer, "CORPUS", reversed_corpus)

    assert [a.id for a in answer_query("wool")] == ["FTA-900", "FTA-901", "FTA-902"]


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
    # "immigration" has no corpus entry (named but unsourced per corpus.py's SECTORS_IN_SCOPE
    # comment); matching on "india" alone would wrongly surface an unrelated cross-sector entry
    # instead of escalating to INZBC.
    assert answer_query("immigration in India") == []
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


def test_answer_surfaces_structured_tariff_fields_when_sourced() -> None:
    # #185: a member asking "what's the current tariff on wool" needs a queryable value, not
    # `treatment` re-parsed. Wool (FTA-005) has every structured field sourced.
    answers = answer_query("wool")
    assert len(answers) == 1
    answer = answers[0]
    assert answer.direction is TradeDirection.NZ_EXPORTS_TO_INDIA
    assert answer.current_tariff == "2.75%"
    assert answer.fta_commencement_tariff == "0% (eliminated day 1)"
    assert answer.final_tariff == "0% (eliminated)"
    assert answer.implementation_period_years == 0


def test_answer_carries_staged_reductions_when_phase_in_is_not_immediate() -> None:
    # Forestry (FTA-004) phases in over years rather than eliminating day one, so
    # staged_reductions is the field that distinguishes "0% now" from "0% in 7 years".
    answers = answer_query("forestry")
    assert len(answers) == 1
    assert answers[0].staged_reductions == (
        "Remainder of forestry trade interests phased out over 5-7 years"
    )
    assert answers[0].implementation_period_years == 7


def test_answer_passes_through_none_for_unsourced_tariff_fields() -> None:
    # Milk/cheese/butter (FTA-013) is excluded from concessions and has no current-tariff
    # callout in the source table (corpus.py docstring: "current_tariff stays unset rather than
    # guessed"). None here must mean "not yet sourced", not "0%" or silently omitted.
    answers = answer_query("milk cheese butter")
    matches = [a for a in answers if a.topic == "Dairy - milk, cheese, butter"]
    assert len(matches) == 1
    answer = matches[0]
    assert answer.current_tariff is None
    assert answer.fta_commencement_tariff is None
    assert answer.staged_reductions is None
    assert answer.final_tariff is None
    assert answer.implementation_period_years is None
    assert answer.direction is TradeDirection.NZ_EXPORTS_TO_INDIA


# --- #187: three-audience depth split -------------------------------------------------------


def test_depth_defaults_to_member() -> None:
    answers = answer_query_at_depth("dairy")
    assert answers
    assert all(isinstance(a, MemberAnswer) for a in answers)


def test_member_depth_returns_member_answer_shape() -> None:
    answers = answer_query_at_depth("wool", Depth.MEMBER)
    assert len(answers) == 1
    assert isinstance(answers[0], MemberAnswer)
    assert answers[0].topic == "Wool"
    assert answers[0].confirmed is True


def test_member_answer_carries_the_same_sourced_content_as_answer_query() -> None:
    # MemberAnswer is a distinct type from ExplainerAnswer (not a re-export of it), but every
    # field it does carry must match answer_query()'s result exactly - the audience split must
    # not silently change *content*, only which fields are exposed.
    legacy = answer_query("dairy")[0]
    member = answer_query_at_depth("dairy", Depth.MEMBER)[0]
    assert member.id == legacy.id
    assert member.citation == legacy.citation
    assert member.verified_at == legacy.verified_at
    assert member.treatment == legacy.treatment
    assert member.confidence == legacy.confidence


def test_member_answer_excludes_internal_notes() -> None:
    # The finding Bhanu raised: several corpus entries carry reviewer/drafting notes that are
    # editorial record, not member-facing content. Structural, not conventional - MemberAnswer
    # simply has no `notes` field, so a member-facing renderer cannot read it even by mistake.
    field_names = {f.name for f in fields(MemberAnswer)}
    assert "notes" not in field_names


def test_public_depth_returns_public_answer_shape() -> None:
    answers = answer_query_at_depth("wool", Depth.PUBLIC)
    assert len(answers) == 1
    assert isinstance(answers[0], PublicAnswer)
    assert answers[0].topic == "Wool"


def test_public_answer_carries_citation_and_verified_at() -> None:
    # docs/modules/fta-centre.md requires every material answer - public or member - to carry
    # its citation and source/effective date. A simpler public explanation is not an uncited
    # one, so these must be present, not withheld as "evidence".
    legacy = answer_query("wool")[0]
    public = answer_query_at_depth("wool", Depth.PUBLIC)[0]
    assert public.citation == legacy.citation
    assert public.verified_at == legacy.verified_at


def test_public_answer_excludes_internal_only_fields() -> None:
    # What's actually withheld at PUBLIC: the internal `id`, the raw `source_tier` number, and
    # drafting `notes` - reviewer-facing detail with no public-facing use. Structural exclusion,
    # the same discipline NoMatch already uses in this module.
    field_names = {f.name for f in fields(PublicAnswer)}
    assert "id" not in field_names
    assert "notes" not in field_names
    assert "source_tier" not in field_names
    assert "citation" in field_names
    assert "verified_at" in field_names


def test_public_answer_carries_status_line_and_disclaimer() -> None:
    for answer in answer_query_at_depth("wine", Depth.PUBLIC):
        assert answer.disclaimer == DISCLAIMER == AI_INFORMATION_STANDARD
        assert "not yet in force" in answer.status_line.lower()


def test_internal_depth_returns_internal_answer_shape() -> None:
    answers = answer_query_at_depth("wool", Depth.INTERNAL)
    assert len(answers) == 1
    assert isinstance(answers[0], InternalAnswer)
    assert answers[0].topic == "Wool"
    assert answers[0].confirmed is True


def test_internal_answer_carries_full_evidence_trail() -> None:
    member = answer_query("dairy")[0]
    internal = answer_query_at_depth("dairy", Depth.INTERNAL)[0]
    assert internal.id == member.id
    assert internal.citation == member.citation
    assert internal.verified_at == member.verified_at
    assert internal.source_tier in (1, 2)
    # notes is whatever the corpus entry carries (often None) — presence of the field, not a
    # specific value, is what #187 asks for at this tier.
    assert hasattr(internal, "notes")


def test_all_three_depths_preserve_ranking_order() -> None:
    member = answer_query("dairy")
    public = answer_query_at_depth("dairy", Depth.PUBLIC)
    internal = answer_query_at_depth("dairy", Depth.INTERNAL)
    assert [a.topic for a in member] == [a.topic for a in public] == [a.topic for a in internal]
    assert len(member) > 1  # guards against a query that only ever ties one entry


def test_no_match_is_depth_independent() -> None:
    for depth in (Depth.PUBLIC, Depth.MEMBER, Depth.INTERNAL):
        assert answer_query_at_depth("semiconductor export controls", depth) == []


def test_unconfirmed_entry_suppressed_at_every_depth() -> None:
    for depth in (Depth.PUBLIC, Depth.MEMBER, Depth.INTERNAL):
        assert answer_query_at_depth("tariff line", depth) == []


def test_structured_tariff_fields_reach_every_depth() -> None:
    # #185's structured tariff fields are answer content, not evidence - every audience gets
    # the same queryable value.
    member_legacy = answer_query("wool")[0]
    public = answer_query_at_depth("wool", Depth.PUBLIC)[0]
    member = answer_query_at_depth("wool", Depth.MEMBER)[0]
    internal = answer_query_at_depth("wool", Depth.INTERNAL)[0]
    for field in ("current_tariff", "fta_commencement_tariff", "final_tariff", "direction"):
        assert getattr(public, field) == getattr(member_legacy, field)
        assert getattr(member, field) == getattr(member_legacy, field)
        assert getattr(internal, field) == getattr(member_legacy, field)
