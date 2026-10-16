"""PostgreSQL integration tests for `PostgresEmbeddingStore` and `cosine_similarity` (#63).

Skipped locally when `DATABASE_URL` is not set; executed in CI against the Postgres service
container with `database/schema.sql` applied.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from types import SimpleNamespace

import psycopg
import pytest

from services.api.embeddings import (
    DimensionMismatchError,
    EmbeddingDocument,
    EmbeddingService,
    PostgresEmbeddingStore,
    RetrievalFilters,
    StoredEmbedding,
)
from services.api.model_gateway import DEFAULT_EMBEDDING_MODEL, ModelGateway
from services.api.prompt_boundary import PromptSource
from services.api.tests.test_embeddings import SEEDED_FTA_FIXTURES, _FakeEmbeddingClient

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - embeddings persistence tests need a real Postgres",
)


@pytest.fixture(autouse=True)
def _redaction_policy(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "name": "email",
                        "pattern": r"[\w.+-]+@[\w-]+\.[\w.]+",
                        "replacement": "[redacted:email]",
                        "example": "contact sunil@example.test",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("REDACTION_POLICY_PATH", str(policy))


@pytest.fixture
def db_conn() -> Iterator[psycopg.Connection]:
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL, autocommit=False) as conn:
        yield conn
        conn.rollback()


def test_postgres_store_upserts_filters_and_ranks_nearest_neighbours(
    db_conn: psycopg.Connection,
) -> None:
    mapping = {doc.text: vec for doc, vec in SEEDED_FTA_FIXTURES}
    mapping["greasy wool duty"] = (0.99, 0.08, 0.04, 0.12)
    mapping["dairy quota"] = (0.06, 0.98, 0.04, 0.10)

    client = _FakeEmbeddingClient(mapping)
    gateway = ModelGateway(client=client, usage_sink=lambda _u: None)
    store = PostgresEmbeddingStore(db_conn)
    service = EmbeddingService(gateway, store)

    service.index_documents(
        [doc for doc, _ in SEEDED_FTA_FIXTURES],
        source=PromptSource.PUBLIC_SOURCE,
    )

    fetched = store.get(
        "fta_corpus",
        "FTA-CH2-WOOL-01",
        embedding_model=DEFAULT_EMBEDDING_MODEL,
    )
    assert fetched is not None
    assert fetched.sector == "wool"
    assert fetched.source_tier == 1

    # Ranked nearest-neighbour hits with score threshold and metadata filter in SQL.
    wool_hits = service.retrieve(
        "fta_corpus",
        "What is the greasy wool duty schedule?",
        source=PromptSource.PUBLIC_SOURCE,
        min_score=0.75,
        filters=RetrievalFilters(sector="wool", max_source_tier=2),
    )
    assert [hit.record_id for hit in wool_hits] == [
        "FTA-CH2-WOOL-01",
        "FTA-CH3-ROO-01",
    ]
    assert wool_hits[0].score > wool_hits[1].score

    # Idempotent upsert updates title/hash in place without duplicating rows.
    updated_doc = EmbeddingDocument(
        corpus="fta_corpus",
        record_id="FTA-CH2-WOOL-01",
        title="Updated wool schedule title",
        text=SEEDED_FTA_FIXTURES[0][0].text,
        sector="wool",
        jurisdiction="bilateral",
        source_tier=1,
    )
    service.index_document(updated_doc, source=PromptSource.PUBLIC_SOURCE)
    refetched = store.get(
        "fta_corpus",
        "FTA-CH2-WOOL-01",
        embedding_model=DEFAULT_EMBEDDING_MODEL,
    )
    assert refetched is not None and refetched.title == "Updated wool schedule title"


def test_postgres_store_refuses_dimension_mismatch_and_supports_dedupe(
    db_conn: psycopg.Connection,
) -> None:
    store = PostgresEmbeddingStore(db_conn)
    store.upsert(
        StoredEmbedding(
            corpus="sip_candidates",
            record_id="cand-pg-1",
            title="NZ-India wool tariff elimination confirmed",
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            dimensions=4,
            embedding=(0.95, 0.15, 0.05, 0.10),
            content_sha256="b" * 64,
            sector="wool",
            jurisdiction="bilateral",
            source_tier=1,
        )
    )
    with pytest.raises(DimensionMismatchError):
        store.search(
            "sip_candidates",
            (1.0, 0.0),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
        )

    client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **_kw: SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.96, 0.14, 0.04, 0.11])],
                usage=SimpleNamespace(input_tokens=12),
            )
        )
    )
    gateway = ModelGateway(client=client, usage_sink=lambda _u: None)
    service = EmbeddingService(gateway, store)
    candidate = EmbeddingDocument(
        corpus="sip_candidates",
        record_id="cand-pg-2",
        title="India removes duty on NZ wool exports",
        text="India removes duty on NZ wool exports under bilateral agreement",
        sector="wool",
        jurisdiction="bilateral",
        source_tier=2,
    )
    dupes = service.find_semantic_duplicates(
        "sip_candidates",
        candidate,
        source=PromptSource.PUBLIC_SOURCE,
        threshold=0.90,
        index_after_search=True,
    )
    assert len(dupes) == 1
    assert dupes[0].matched_record_id == "cand-pg-1"
