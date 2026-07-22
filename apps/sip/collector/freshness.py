"""SIP-050 section 7 (Coverage Window and Freshness): computes whether a candidate's published
time falls in the run's locked 24h window.

Only the mechanical part of section 7 is implemented here - "In Window" (published_at falls in
`[coverage_start_utc, coverage_end_utc)`, inclusive start / exclusive end per the doc) and
"Unverified" (a timestamp that can't be confirmed, mapped to `None` per
`Candidate.in_coverage_window`'s optional bool - "do not present as fresh" means do not default
to True). "Active Carry-Forward", "Context", and "Stale" all require judgment about whether an
older item still has a live deadline, event, or trigger (SIP-050 section 15) - that's an
analyst/model-recommendation call, not something derivable from a timestamp alone, so this
module doesn't attempt it.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _to_aware_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # A timestamp with no confirmed timezone cannot be confidently placed in a UTC-anchored
        # window - this is exactly SIP-050 section 7's "Unverified" status, not "assume UTC".
        return None
    return parsed.astimezone(timezone.utc)


def compute_in_coverage_window(
    published_at: str | None, coverage_start_utc: str, coverage_end_utc: str
) -> bool | None:
    """SIP-050 section 7: inclusive start, exclusive end. Returns `None` (Unverified) rather
    than guessing when `published_at` is missing, unparseable, or timezone-naive, or when either
    window bound is.
    """
    published = _to_aware_utc(published_at)
    start = _to_aware_utc(coverage_start_utc)
    end = _to_aware_utc(coverage_end_utc)
    if published is None or start is None or end is None:
        return None
    return start <= published < end
