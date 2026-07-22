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

from datetime import datetime

from pydantic import BaseModel

from apps.sip.pipeline.models import Candidate

# GDELT's DOC 2.0 API `seendate` field; RSS entries are parsed by parse_published_at's
# fromisoformat branches instead (agent.py stores str(datetime) there, e.g. from
# email.utils.parsedate_to_datetime).
_GDELT_DATE_FORMATS = ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S")


def parse_published_at(raw: str | None) -> str | None:
    """Best-effort parse of the agent's `published` field into an ISO 8601 string.

    Returns None on anything empty or unrecognised rather than guessing — a missing capture
    time is preferable to a wrong one.
    """
    if not raw or not raw.strip():
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
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue

    return None


class MappedCandidate(BaseModel):
    """A Candidate ready to write, plus the agent's raw source label.

    `candidate.source_id` is left unset unless `source_lookup` resolves it: the agent only
    emits a free-text source name (e.g. "RNZ Business", "GDELT"), and schemas/api-contract.md
    has no source_library lookup endpoint yet to resolve a name to its DB id (tracked in
    docs/workstreams/roshan.md's blocked list). `source_name` is kept alongside so a resolver
    can be applied later without re-reading the agent's output.
    """

    candidate: Candidate
    source_name: str


def map_article(
    article: dict, run_id: str, source_lookup: dict[str, str] | None = None
) -> MappedCandidate:
    """Maps one `clean_articles()` output dict onto a Candidate for run `run_id`.

    `source_lookup` maps a source name (`article["source"]`) to a `source_library.id`; omit it
    (or leave a name unmatched) to capture the candidate with `source_id=None`.

    KNOWN SIMPLIFICATION - `in_coverage_window` is hardcoded True, not computed against the
    locked window: SIP-184 step 2 locks a *fixed* 24h Pacific/Auckland window (previous day
    07:00 to current day 07:00) at run start, but agent.py's `is_recent_article`/`fetch_news`
    filter on a *rolling* cutoff (`datetime.now(timezone.utc) - max_age_hours`) computed whenever
    the agent happens to run - the two windows are usually close but are not the same boundary,
    and can disagree by however late/early the agent's run lands relative to 07:00 NZT. This is
    accepted here because `articles` is still always the agent's own within-window output, not
    an arbitrary mix, but it is not the same thing as evaluating each item against the run's
    actual locked `coverage_start_utc`/`coverage_end_utc`. Fix properly by comparing each
    article's parsed `published_at` against the run's locked window once the run object is
    threaded through here, rather than trusting the agent's rolling filter as a proxy for it.
    """
    source_name = str(article.get("source", "")).strip()
    source_id = source_lookup.get(source_name) if source_lookup else None

    candidate = Candidate(
        run_id=run_id,
        headline=article["title"],
        source_id=source_id,
        url=article.get("url") or None,
        summary=article.get("description") or None,
        published_at=parse_published_at(article.get("published")),
        in_coverage_window=True,
    )
    return MappedCandidate(candidate=candidate, source_name=source_name)


def map_articles(
    articles: list[dict], run_id: str, source_lookup: dict[str, str] | None = None
) -> list[MappedCandidate]:
    return [map_article(article, run_id, source_lookup) for article in articles]
