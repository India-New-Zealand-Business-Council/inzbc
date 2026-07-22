"""FTA Opportunity Explainer: sector/product query -> sourced answer.

Matches a member's query against apps/fta/corpus.py by shared keywords only - no model call, no
guessing beyond what's in the corpus. Per docs/modules/fta-centre.md's definition of done,
"unsupported-answer behaviour" (no corpus match) must route to INZBC, never invent an answer -
`answer_query` returning `[]` is that signal; the caller is expected to show a "talk to INZBC"
prompt rather than treat an empty list as an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .corpus import CORPUS, FTA_STATUS_LINE, TariffOutcome

# Disclaimer wording is explicitly still "INZBC to confirm" (docs/modules/fta-centre.md's
# dependencies) - this is a placeholder, not an authored disclaimer, and must not be shown to a
# member as-is.
DISCLAIMER_PLACEHOLDER = "[[INZBC-approved disclaimer wording pending]]"

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
    notes: str | None = None


_NEXT_STEP = (
    "Confirm the exact tariff line in the FTA's Annex 2A schedule, or contact INZBC for "
    "product-specific guidance."
)


def _to_answer(entry: TariffOutcome) -> ExplainerAnswer:
    return ExplainerAnswer(
        topic=entry.topic,
        sector=entry.sector,
        treatment=entry.treatment,
        confirmed=entry.confirmed,
        citation=entry.citation,
        verified_at=entry.verified_at,
        status_line=FTA_STATUS_LINE,
        jurisdiction=JURISDICTION,
        next_step=_NEXT_STEP,
        disclaimer=DISCLAIMER_PLACEHOLDER,
        notes=entry.notes,
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
