"""Resolves source names to `source_library` ids via `GET /api/source-library`
(schemas/api-contract.md), added in PR #25 - this is what `map_article`, `map_articles`,
`ingest_articles`, and `record_source_outcome`'s `source_lookup` parameter was waiting on.
"""

from __future__ import annotations

from apps.sip.pipeline.client import SipPipelineClient
from apps.sip.pipeline.models import SourceLibraryEntry


def build_source_lookup(rows: list[dict]) -> dict[str, str]:
    """Builds a name -> id map from `GET /api/source-library`'s raw response rows.

    Only active entries are included - a deactivated source_library row should not resolve for
    a new candidate or source-check write. If two active rows share a name, the later one in
    `rows` wins; the API contract doesn't document name uniqueness, so this doesn't assume it.
    """
    lookup: dict[str, str] = {}
    for row in rows:
        entry = SourceLibraryEntry(**row)
        if entry.active:
            lookup[entry.name] = entry.id
    return lookup


def fetch_source_lookup(client: SipPipelineClient) -> dict[str, str]:
    """Fetches the source library and builds a name -> id map in one call."""
    return build_source_lookup(client.list_source_library())
