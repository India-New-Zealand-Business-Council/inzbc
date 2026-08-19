"""FTA Opportunity Explainer: sector/product query -> sourced answer.

Ranks matches against apps/fta/corpus.py by shared keyword relevance (#54) - no model call, no
guessing beyond what's in the corpus, no vector/embedding service. Per docs/modules/fta-centre.md's
definition of done, "unsupported-answer behaviour" (no corpus match) must route to INZBC, never
invent an answer - `answer_query` returning `[]` is that signal, and `no_match()` builds the Action
Required state a caller renders instead of treating the empty list as an error.

`NoMatch` is deliberately **not** shaped like `ExplainerAnswer`: it carries no topic, sector,
treatment, citation or verified_at. A renderer therefore cannot feed it through the sourced-answer
path and present escalation guidance as if it were an FTA finding - the one failure this whole
module exists to prevent. The distinction is structural, not a naming convention, and
test_explainer.py asserts it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date

from .corpus import CORPUS, FTA_STATUS_LINE, TariffOutcome, TradeDirection
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


# Topic keywords score higher than sector keywords: "wool" in an entry's topic is a precise
# product match, but "agriculture" in its sector is shared by most of the corpus and should not
# outweigh a specific topic hit. Both are then weighted by inverse document frequency, so a term
# nearly every confirmed entry shares (few of these survive stopword filtering, but sector words
# like "agriculture"/"dairy" still recur) contributes less than a term unique to one or two
# entries - the standard ranked-retrieval idea, sized to an 18-row corpus rather than a vector
# index. This is what "better ranking on multi-term queries" (#54's acceptance criterion) means
# here: a query sharing more, rarer terms with an entry ranks it above one sharing fewer, commoner
# terms, rather than every keyword-overlapping entry being an unordered, equally-weighted match.
_TOPIC_WEIGHT = 2.0
_SECTOR_WEIGHT = 1.0


def _document_frequencies() -> dict[str, int]:
    """How many confirmed entries' topic+sector keywords contain each term.

    Computed over confirmed entries only: unconfirmed entries (e.g. FTA-003) never reach a member
    (see `answer_query`), so their vocabulary should not influence the ranking of ones that do.
    """
    counts: dict[str, int] = {}
    for entry in CORPUS:
        if not entry.confirmed:
            continue
        for keyword in _keywords(entry.topic) | _keywords(entry.sector):
            counts[keyword] = counts.get(keyword, 0) + 1
    return counts


_DOCUMENT_FREQUENCIES = _document_frequencies()
_CONFIRMED_ENTRY_COUNT = sum(1 for entry in CORPUS if entry.confirmed)


def _idf(keyword: str) -> float:
    """Smoothed inverse document frequency. `+1` on both sides keeps this positive and finite
    even for a keyword in every confirmed entry or (defensively) one seen in none.
    """
    df = _DOCUMENT_FREQUENCIES.get(keyword, 0)
    return math.log((_CONFIRMED_ENTRY_COUNT + 1) / (df + 1)) + 1


def _entry_keyword_weights(entry: TariffOutcome) -> dict[str, float]:
    """keyword -> relevance weight for one entry, combining topic/sector position weight with
    the term's corpus-wide rarity. A keyword present in both topic and sector accumulates both.
    """
    weights: dict[str, float] = {}
    for keyword in _keywords(entry.topic):
        weights[keyword] = weights.get(keyword, 0.0) + _TOPIC_WEIGHT * _idf(keyword)
    for keyword in _keywords(entry.sector):
        weights[keyword] = weights.get(keyword, 0.0) + _SECTOR_WEIGHT * _idf(keyword)
    return weights


def _relevance_score(query_keywords: set[str], entry: TariffOutcome) -> float:
    weights = _entry_keyword_weights(entry)
    return sum(weights.get(keyword, 0.0) for keyword in query_keywords)


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
    # Structured tariff fields (#185): a member asking "what's the current tariff on wool" needs
    # a queryable value, not `treatment` re-parsed. Passed through from TariffOutcome exactly as
    # sourced - None means "not yet sourced for this entry", never "zero" or "unchanged". See
    # TariffOutcome's docstring in corpus.py for why these are free text, not parsed percentages.
    direction: TradeDirection | None = None
    current_tariff: str | None = None
    fta_commencement_tariff: str | None = None
    staged_reductions: str | None = None
    final_tariff: str | None = None
    implementation_period_years: int | None = None


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
        direction=entry.direction,
        current_tariff=entry.current_tariff,
        fta_commencement_tariff=entry.fta_commencement_tariff,
        staged_reductions=entry.staged_reductions,
        final_tariff=entry.final_tariff,
        implementation_period_years=entry.implementation_period_years,
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
    """Ranks `query` against the corpus by weighted shared-keyword relevance with each entry's
    topic and sector (topic matches and rarer terms score higher - see `_relevance_score`).

    Returns every matching **confirmed** entry, most relevant first (a sector query like "dairy"
    naturally maps to more than one tariff outcome, and a multi-term query should surface the
    entry sharing the most, rarest terms before one sharing only a common sector word).
    `confirmed=False` corpus entries (e.g. the still-unconfirmed ~70% tariff-line figure) are
    never surfaced here - docs/fta-source-corpus.md explicitly says not to cite that figure in
    the Explainer until it's confirmed against a primary source, so a query that only matches an
    unconfirmed entry gets the same `[]` as no match at all, not a caveated figure.

    Returns `[]` when nothing confirmed matches, including when `query` is empty or only
    stopwords - the caller routes that to INZBC rather than guessing. Ranking only orders and
    never widens the match set: an entry with zero shared keywords still scores 0 and is
    excluded, exactly as before.
    """
    query_keywords = _keywords(query)
    if not query_keywords:
        return []

    scored = [
        (entry, _relevance_score(query_keywords, entry)) for entry in CORPUS if entry.confirmed
    ]
    matched = [(entry, score) for entry, score in scored if score > 0]
    # entry.id as the tiebreaker: deterministic, stable ordering for entries that score equally
    # (e.g. two entries sharing the same single sector keyword and nothing else).
    matched.sort(key=lambda pair: (-pair[1], pair[0].id))
    return [_to_answer(entry) for entry, _score in matched]
