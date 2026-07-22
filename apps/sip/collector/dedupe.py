"""Duplicate detection for candidate capture (SIP-184 step 6's "duplicate status" field).

`agent.py`'s own `clean_articles()` already drops exact url/title repeats found within a single
fetch, but nothing dedupes across separate runs (e.g. the same story still circulating a day
later) or across near-identical url/title variants. This compares new articles against already
captured candidates (fetched via `SipPipelineClient.list_candidates`) so a match can be recorded
as `duplicate_of` on capture instead of it being reported twice.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    normalized = url.strip().lower().rstrip("/")
    return normalized or None


def normalize_title(title: str | None) -> str | None:
    if not title:
        return None
    normalized = _WHITESPACE.sub(" ", title.strip().lower())
    return normalized or None


def find_duplicate_of(article: dict, existing_candidates: list[dict]) -> str | None:
    """Returns the `id` of an existing candidate this article duplicates, matched first by
    normalized url and then by normalized headline, or None if nothing matches.
    """
    url = normalize_url(article.get("url"))
    if url:
        for candidate in existing_candidates:
            if normalize_url(candidate.get("url")) == url:
                return candidate.get("id")

    title = normalize_title(article.get("title"))
    if title:
        for candidate in existing_candidates:
            if normalize_title(candidate.get("headline")) == title:
                return candidate.get("id")

    return None
