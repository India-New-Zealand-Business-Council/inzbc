"""Writes an agent run's articles into an existing SIP run as candidates.

Assumes the run itself already exists (created via `SipPipelineClient.create_run` — this
module has no way to invent `initiated_by`, `prompt_version` or the coverage window; those
come from the run authority step, SIP-184 step 1, not the collection engine).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

from apps.sip.pipeline.client import SipApiError, SipPipelineClient

from .mapping import map_article
from .source_lookup import SourceNameLookup


class MalformedArticleError(TypeError):
    """Raised when an article is not a dict. Caught as one failed item, unlike a bare
    `except TypeError` which would also swallow unrelated type errors from mapping/client code.
    """


@dataclass
class IngestFailure:
    source_name: str
    headline: str
    error: str


@dataclass
class IngestResult:
    created: list[dict] = field(default_factory=list)
    failed: list[IngestFailure] = field(default_factory=list)


def ingest_articles(
    client: SipPipelineClient,
    run_id: str,
    articles: list[dict],
    source_name_lookup: SourceNameLookup | None = None,
) -> IngestResult:
    """POSTs each of `articles` (daily-india-nz-news-agent's `clean_articles()` output) to
    `/api/candidates` for `run_id`. Continues past individual mapping *or* write failures instead
    of aborting the batch — SIP-185's fallback rules require never silently dropping a
    potentially relevant item, so one malformed article (e.g. a missing `title`) must not abort
    every later item in the batch; each article is mapped and sent inside its own try/except,
    not mapped eagerly for the whole batch up front.
    """
    result = IngestResult()
    for article in articles:
        source_name = ""
        headline = ""
        try:
            if not isinstance(article, dict):
                raise MalformedArticleError(
                    f"expected a dict article, got {type(article).__name__}"
                )
            source_name = str(article.get("source", "")).strip()
            headline = str(article.get("title", ""))
            mapped = map_article(article, run_id, source_name_lookup)
            result.created.append(client.create_candidate(mapped.candidate))
        except (SipApiError, ValidationError, KeyError, MalformedArticleError) as error:
            result.failed.append(
                IngestFailure(source_name=source_name, headline=headline, error=str(error))
            )
    return result
