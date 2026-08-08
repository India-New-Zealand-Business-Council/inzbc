from __future__ import annotations

import pytest

from apps.sip.collector.ingest import ingest_articles
from apps.sip.pipeline.client import SipApiError

RUN_ID = "11111111-1111-1111-1111-111111111111"


class _FakeClient:
    """Stands in for SipPipelineClient: records what it was asked to create, fails on demand."""

    def __init__(self, fail_headlines: set[str] | None = None):
        self.fail_headlines = fail_headlines or set()
        self.created_payloads: list[dict] = []

    def create_candidate(self, candidate, actor_id) -> dict:
        if candidate.headline in self.fail_headlines:
            raise SipApiError(500, "server error")
        payload = candidate.model_dump(mode="json", exclude_none=True)
        payload["actor_id"] = actor_id
        self.created_payloads.append(payload)
        return {"id": "created", **payload}


def _article(**overrides: object) -> dict:
    base = {
        "title": "India, NZ discuss FTA next steps",
        "description": "Officials met to progress trade talks.",
        "url": "https://example.com/article",
        "source": "RNZ Business",
        "published": "2026-07-21 19:32:00+00:00",
        "score": 34,
        "nz_relevance_score": 15,
        "sectors": "Trade and FTA",
    }
    base.update(overrides)
    return base


def test_ingest_articles_creates_every_candidate() -> None:
    client = _FakeClient()
    articles = [_article(title="First"), _article(title="Second")]

    result = ingest_articles(client, RUN_ID, articles, "actor-1")

    assert len(result.created) == 2
    assert result.failed == []
    assert len(client.created_payloads) == 2


def test_ingest_articles_collects_failures_without_aborting_the_batch() -> None:
    client = _FakeClient(fail_headlines={"First"})
    articles = [_article(title="First"), _article(title="Second")]

    result = ingest_articles(client, RUN_ID, articles, "actor-1")

    assert len(result.created) == 1
    assert len(result.failed) == 1
    assert result.failed[0].headline == "First"
    assert result.failed[0].source_name == "RNZ Business"
    assert "server error" in result.failed[0].error
    # The failure did not stop the second candidate from being written.
    assert client.created_payloads[0]["headline"] == "Second"


def test_ingest_articles_handles_non_string_published_without_aborting_the_batch() -> None:
    # A non-string `published` value used to raise AttributeError inside parse_published_at,
    # which this function's per-item except didn't catch - aborting the whole batch. It's now
    # treated as unparseable (published_at=None) instead of crashing, so this article succeeds
    # like any other, just without a captured publish time.
    client = _FakeClient()
    articles = [
        _article(title="Before"),
        _article(title="Malformed", published=20260721193200),
        _article(title="After"),
    ]

    result = ingest_articles(client, RUN_ID, articles, "actor-1")

    assert {c["headline"] for c in client.created_payloads} == {"Before", "Malformed", "After"}
    assert result.failed == []
    malformed_payload = next(c for c in client.created_payloads if c["headline"] == "Malformed")
    assert "published_at" not in malformed_payload


def test_ingest_articles_records_a_malformed_article_without_aborting_the_batch() -> None:
    # A missing "title" fails inside map_article (Candidate.headline is required) - that must
    # not prevent the well-formed articles around it from being captured.
    client = _FakeClient()
    malformed = _article()
    del malformed["title"]
    articles = [_article(title="Before"), malformed, _article(title="After")]

    result = ingest_articles(client, RUN_ID, articles, "actor-1")

    assert {c["headline"] for c in client.created_payloads} == {"Before", "After"}
    assert len(result.failed) == 1
    assert result.failed[0].headline == ""
    assert result.failed[0].source_name == "RNZ Business"


@pytest.mark.parametrize("bad", ["not an article", 123])
def test_ingest_articles_records_a_non_dict_item_without_aborting_the_batch(bad: object) -> None:
    # A non-dict item (a bare string, an int) would raise before the field access if that access
    # ran outside the per-item try - it must be recorded as one failure, not abort the batch.
    client = _FakeClient()
    articles = [_article(title="Before"), bad, _article(title="After")]

    result = ingest_articles(client, RUN_ID, articles, "actor-1")

    assert {c["headline"] for c in client.created_payloads} == {"Before", "After"}
    assert len(result.failed) == 1
    assert result.failed[0].headline == ""
    assert result.failed[0].source_name == ""
