"""Maps daily-india-nz-news-agent's article output onto SIP Candidate records.

The shape mapped here is `clean_articles()`'s output in that repo's `agent.py`:
    {"title", "description", "url", "source", "published", "score", "nz_relevance_score",
     "sectors"}
That repo is the only source of truth for this shape; do not change this module to match a
guessed or assumed shape instead.

Only SIP-184 step 5 (raw candidate capture) is done here. `nz_relevance`/`india_relevance`/
`member_relevance` (0-5), `signal`, `confidence`, `duplicate_of`, `included`, `reason`, and
`proposed_routing` are later SOP steps (6-7) and are intentionally left unset — the agent's own
`score` and `nz_relevance_score` are unrelated point scales, not the approved 0-5 relevance
rubric, so forcing them into those fields would misrepresent unscored candidates as scored ones.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from apps.sip.pipeline.models import Candidate

from .source_lookup import SourceNameLookup

# GDELT's DOC 2.0 API `seendate` field; RSS entries are parsed by parse_published_at's
# fromisoformat branches instead (agent.py stores str(datetime) there, e.g. from
# email.utils.parsedate_to_datetime). On Python 3.11+, fromisoformat already parses the
# "...Z"-suffixed form directly (as UTC), so in practice only the no-separator compact form below
# ever reaches the strptime loop - the "...Z" entry is kept as a defensive fallback in case that
# changes. GDELT's API documentation states every seendate is UTC, so both formats are parsed as
# UTC explicitly (DTZ007) rather than left as an ambiguous naive datetime.
_GDELT_DATE_FORMATS = ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S")


def parse_published_at(raw: object) -> str | None:
    """Best-effort parse of the agent's `published` field into an ISO 8601 string.

    Returns None on anything empty, non-string, or unrecognised rather than guessing or raising
    - the agent's output is untrusted external data, so a wrong-typed value (e.g. an int) here
    is treated the same as an unparseable one, not a crash. A missing capture time is preferable
    to a wrong one.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip()

    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        pass

    try:
        return datetime.fromisoformat(value.replace(" ", "T", 1)).isoformat()
    except ValueError:
        pass

    for fmt in _GDELT_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC).isoformat()
        except ValueError:
            continue

    return None


class MappedCandidate(BaseModel):
    """A Candidate ready to write, plus the agent's raw source label.

    `candidate.source_id` is left unset unless `source_name_lookup` resolves it: the agent only
    emits a free-text source name (e.g. "RNZ Business", "GDELT"), and `source_library.name` is
    display/candidate-capture only — not unique (`schemas/api-contract.md`) — so an unmatched or
    ambiguous name degrades to unset rather than guessing. Build `source_name_lookup` via
    `source_lookup.build_source_lookups(client.get_source_library())`. `source_name` is kept
    alongside so a resolver can be applied later without re-reading the agent's output.
    """

    candidate: Candidate
    source_name: str


def _in_locked_window(published_at: str | None, coverage_window: tuple[str, str] | None) -> bool | None:
    """Compares a parsed `published_at` against the run's locked coverage window.

    Returns `None`, not `False`, when either side is missing or unparseable: SIP-184 step 2's
    window is a fact about the run, and an article whose publish time is unknown or a caller that
    never supplied a window are both "we don't know", not "outside the window". Writing `False`
    for either would store a fabricated coverage fact — the same category of thing this codebase
    refuses to do for statistics or board names.
    """
    if coverage_window is None or published_at is None:
        return None
    start_utc, end_utc = coverage_window
    try:
        published_dt = datetime.fromisoformat(published_at)
        start_dt = datetime.fromisoformat(start_utc)
        end_dt = datetime.fromisoformat(end_utc)
    except ValueError:
        return None
    return start_dt <= published_dt < end_dt


def map_article(
    article: dict,
    run_id: str,
    source_name_lookup: SourceNameLookup | None = None,
    coverage_window: tuple[str, str] | None = None,
) -> MappedCandidate:
    """Maps one `clean_articles()` output dict onto a Candidate for run `run_id`.

    `source_name_lookup` maps a source name (`article["source"]`) to a `source_library.id`; omit it
    (or leave a name unmatched) to capture the candidate with `source_id=None`.

    `coverage_window` is the run's locked `(coverage_start_utc, coverage_end_utc)` from SIP-184
    step 2 - pass it so `in_coverage_window` is computed against the run's actual fixed 24h
    Pacific/Auckland window rather than trusting agent.py's rolling `max_age_hours` cutoff as a
    proxy for it (the two windows are usually close but are not the same boundary). Omitting it
    leaves `in_coverage_window` unset (`None`), not `True` - an uncomputed fact should read as
    unknown, not as a fabricated "yes".
    """
    source_name = str(article.get("source", "")).strip()
    source_id = source_name_lookup.get(source_name) if source_name_lookup else None
    published_at = parse_published_at(article.get("published"))

    candidate = Candidate(
        run_id=run_id,
        headline=article["title"],
        source_id=source_id,
        url=article.get("url") or None,
        summary=article.get("description") or None,
        published_at=published_at,
        in_coverage_window=_in_locked_window(published_at, coverage_window),
    )
    return MappedCandidate(candidate=candidate, source_name=source_name)


def map_articles(
    articles: list[dict],
    run_id: str,
    source_name_lookup: SourceNameLookup | None = None,
    coverage_window: tuple[str, str] | None = None,
) -> list[MappedCandidate]:
    return [
        map_article(article, run_id, source_name_lookup, coverage_window) for article in articles
    ]
