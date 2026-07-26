"""FTA Opportunity Explainer: sector/product query -> sourced answer.

Matches a member's query against apps/fta/corpus.py by shared keywords only - no model call, no
guessing beyond what's in the corpus. Per docs/modules/fta-centre.md's definition of done,
"unsupported-answer behaviour" (no corpus match) must route to INZBC, never invent an answer -
`answer_query` returning `[]` is that signal, and `no_match()` builds the Action Required state a
caller renders instead of treating the empty list as an error.

`NoMatch` is deliberately **not** shaped like `ExplainerAnswer`: it carries no topic, sector,
treatment, citation or verified_at. A renderer therefore cannot feed it through the sourced-answer
path and present escalation guidance as if it were an FTA finding - the one failure this whole
module exists to prevent. The distinction is structural, not a naming convention, and
test_explainer.py asserts it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .corpus import CORPUS, FTA_STATUS_LINE, TariffOutcome
from .standards import AI_INFORMATION_STANDARD, Confidence

DISCLAIMER = AI_INFORMATION_STANDARD

# The `[]` no-match path routes to INZBC rather than guessing; per the Information Confidence
# Standard the caller surfaces that state as Action Required, with this meaning text.
NO_MATCH_CONFIDENCE = Confidence.ACTION_REQUIRED

JURISDICTION = "New Zealand-India"

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "and", "or", "the", "a", "an", "of", "in", "on", "for", "to", "at", "over", "with",
        # Jurisdiction terms: nearly every corpus entry is about NZ-India trade, so these carry
        # no discriminating power - matching on them alone lets an unrelated query (e.g.
        # "education in India") pull in a cross-sector entry instead of correctly returning []
        # and escalating to INZBC.
        "india", "indian", "nz", "new", "zealand",
    }
)


def _keywords(text: str) -> set[str]:
    return {word for word in _WORD_RE.findall(text.lower()) if word not in _STOPWORDS}


@dataclass(frozen=True)
class ExplainerAnswer:
    id: str
    topic: str
    sector: str
    treatment: str
    confirmed: bool
    citation: str
    verified_at: date
    status_line: str
    jurisdiction: str
    next_step: str
    disclaimer: str
    confidence: Confidence
    confidence_meaning: str
    notes: str | None = None


_NEXT_STEP = (
    "Confirm the exact tariff line in the FTA's Annex 2A schedule, or contact INZBC for "
    "product-specific guidance."
)


def _confidence_for(entry: TariffOutcome) -> Confidence:
    """Information Confidence Standard rating (docs/information-standard.md).

    Only confirmed entries reach members (answer_query filters on `confirmed`), so High/Medium
    is decided by the cited source's tier. The Low branch covers an unconfirmed entry if a
    future caller rates one directly - best-available-evidence, independently verify.
    """
    if not entry.confirmed:
        return Confidence.LOW
    return Confidence.HIGH if entry.source_tier == 1 else Confidence.MEDIUM


def _to_answer(entry: TariffOutcome) -> ExplainerAnswer:
    confidence = _confidence_for(entry)
    return ExplainerAnswer(
        id=entry.id,
        topic=entry.topic,
        sector=entry.sector,
        treatment=entry.treatment,
        confirmed=entry.confirmed,
        citation=entry.citation,
        verified_at=entry.verified_at,
        status_line=FTA_STATUS_LINE,
        jurisdiction=JURISDICTION,
        next_step=_NEXT_STEP,
        disclaimer=DISCLAIMER,
        confidence=confidence,
        confidence_meaning=confidence.meaning,
        notes=entry.notes,
    )


@dataclass(frozen=True)
class NoMatch:
    """The Action Required state for a query with no confirmed corpus match.

    Shares only the presentation fields every response carries (status line, jurisdiction,
    disclaimer, confidence). It has none of `ExplainerAnswer`'s evidence fields, so there is no
    field for a renderer to mistake for a sourced finding.
    """

    query: str
    message: str
    next_step: str
    escalation_path: str
    status_line: str
    jurisdiction: str
    disclaimer: str
    confidence: Confidence
    confidence_meaning: str


_NO_MATCH_MESSAGE = (
    "INZBC does not hold a verified answer to this question in its FTA source corpus. Rather "
    "than provide an unverified answer, this query is referred to INZBC."
)

_NO_MATCH_NEXT_STEP = (
    "Check the exact tariff line in the FTA's Annex 2A schedule, or raise an enquiry with INZBC."
)

_NO_MATCH_ESCALATION = (
    "Raise an enquiry with INZBC for product-specific guidance. Where a decision is "
    "time-critical, contact the relevant government agency or a qualified professional adviser "
    "directly."
)


def no_match(query: str) -> NoMatch:
    """Builds the Action Required state a caller renders when `answer_query` returns `[]`.

    Named `no_match` rather than `no_match_answer` on purpose: it is not an answer, and the API
    envelope reports it under `status: "no_match"` with an empty `answers` list.
    """
    return NoMatch(
        query=query,
        message=_NO_MATCH_MESSAGE,
        next_step=_NO_MATCH_NEXT_STEP,
        escalation_path=_NO_MATCH_ESCALATION,
        status_line=FTA_STATUS_LINE,
        jurisdiction=JURISDICTION,
        disclaimer=DISCLAIMER,
        confidence=NO_MATCH_CONFIDENCE,
        confidence_meaning=NO_MATCH_CONFIDENCE.meaning,
    )


def answer_query(query: str) -> list[ExplainerAnswer]:
    """Matches `query` against the corpus by shared keyword with each entry's topic or sector.

    Returns every matching **confirmed** entry (a sector query like "dairy" naturally maps to
    more than one tariff outcome). `confirmed=False` corpus entries (e.g. the still-unconfirmed
    ~70% tariff-line figure) are never surfaced here - docs/fta-source-corpus.md explicitly says
    not to cite that figure in the Explainer until it's confirmed against a primary source, so a
    query that only matches an unconfirmed entry gets the same `[]` as no match at all, not a
    caveated figure.

    Returns `[]` when nothing confirmed matches, including when `query` is empty or only
    stopwords - the caller routes that to INZBC rather than guessing.
    """
    query_keywords = _keywords(query)
    if not query_keywords:
        return []

    matches = [
        entry
        for entry in CORPUS
        if entry.confirmed
        and (query_keywords & _keywords(entry.topic) or query_keywords & _keywords(entry.sector))
    ]
    return [_to_answer(entry) for entry in matches]
