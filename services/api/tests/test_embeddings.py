"""Tests for gateway-backed embeddings, nearest-neighbour retrieval, filters, and dedupe (#63)."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from services.api import model_gateway
from services.api.embeddings import (
    DimensionMismatchError,
    EmbeddingDocument,
    EmbeddingService,
    InMemoryEmbeddingStore,
    RetrievalFilters,
    StoredEmbedding,
    cosine_similarity,
)
from services.api.model_gateway import (
    DEFAULT_EMBEDDING_MODEL,
    GatewayAuditError,
    GatewayCallError,
    GatewayNotConfiguredError,
    ModelGateway,
)
from services.api.prompt_boundary import ProhibitedInputError, PromptSource

# Seeded 4-dimensional unit/directional basis for deterministic semantic fixture testing:
#   axis 0: wool / textiles tariff schedule
#   axis 1: dairy / agriculture quota & sanitary rules
#   axis 2: services / IT & student mobility visa rules
#   axis 3: customs / port logistics & rules of origin
SEEDED_FTA_FIXTURES: tuple[tuple[EmbeddingDocument, tuple[float, ...]], ...] = (
    (
        EmbeddingDocument(
            corpus="fta_corpus",
            record_id="FTA-CH2-WOOL-01",
            title="Annex 2A — Day-one elimination of Indian customs duty on NZ greasy wool (HS 5101)",
            text="Tariff elimination schedule for New Zealand raw and scoured wool exports to India.",
            sector="wool",
            jurisdiction="bilateral",
            source_tier=1,
        ),
        (0.98, 0.10, 0.05, 0.15),
    ),
    (
        EmbeddingDocument(
            corpus="fta_corpus",
            record_id="FTA-CH2-DAIRY-01",
            title="Annex 2A — Dairy tariff-rate quota and infant formula safeguard schedule",
            text="Quota volume, in-quota tariff rate, and safeguard triggers for NZ dairy products.",
            sector="dairy",
            jurisdiction="bilateral",
            source_tier=1,
        ),
        (0.08, 0.97, 0.05, 0.12),
    ),
    (
        EmbeddingDocument(
            corpus="fta_corpus",
            record_id="FTA-CH8-SERVICES-01",
            title="Chapter 8 — Temporary entry of business persons and IT services commitments",
            text="Mobility commitments for software engineers, intra-corporate transferees, and services.",
            sector="services",
            jurisdiction="IN",
            source_tier=1,
        ),
        (0.04, 0.06, 0.99, 0.05),
    ),
    (
        EmbeddingDocument(
            corpus="fta_corpus",
            record_id="FTA-CH3-ROO-01",
            title="Chapter 3 — Rules of origin and self-certification for woollen textiles",
            text="Change-in-tariff-heading and regional value content rules for wool and apparel.",
            sector="wool",
            jurisdiction="NZ",
            source_tier=2,
        ),
        (0.82, 0.05, 0.04, 0.56),
    ),
    (
        EmbeddingDocument(
            corpus="fta_corpus",
            record_id="FTA-NOTE-COMMENTARY-01",
            title="Industry commentary on wool processing partnerships in Ludhiana",
            text="Secondary trade association note on wool spinning mills and duty-free raw wool.",
            sector="wool",
            jurisdiction="IN",
            source_tier=3,
        ),
        (0.91, 0.12, 0.05, 0.20),
    ),
)


@pytest.fixture(autouse=True)
def _configuration(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    for key in (
        "DATABASE_URL",
        "SIP_MODEL_PROVIDER",
        "SIP_MODEL_NAME",
        "SIP_EMBEDDING_MODEL_NAME",
        "SIP_EMBEDDING_INPUT_USD_PER_MILLION",
        "SIP_MODEL_INPUT_USD_PER_MILLION",
        "SIP_MODEL_OUTPUT_USD_PER_MILLION",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(model_gateway, "_RETRY_DELAY_SECONDS", 0)


class _FakeEmbeddingClient:
    """Fake OpenAI client exposing `client.embeddings.create(model=..., input=..., ...)`."""

    def __init__(self, vectors_by_substring: dict[str, Sequence[float]] | list[object]) -> None:
        self._vectors = vectors_by_substring
        self.embeddings = self
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self._vectors, list):
            item = self._vectors.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        text = kwargs["input"]
        for needle, vec in self._vectors.items():
            if needle.lower() in text.lower():
                return SimpleNamespace(
                    data=[SimpleNamespace(embedding=list(vec))],
                    usage=SimpleNamespace(prompt_tokens=16),
                )
        raise AssertionError(f"no fixture vector registered for input: {text!r}")


def _seeded_service() -> tuple[EmbeddingService, _FakeEmbeddingClient, list]:
    mapping: dict[str, Sequence[float]] = {
        doc.text: vec for doc, vec in SEEDED_FTA_FIXTURES
    }
    mapping.update(
        {
            "greasy wool duty": (0.99, 0.08, 0.04, 0.12),
            "dairy infant formula quota": (0.06, 0.98, 0.04, 0.10),
            "software visa mobility": (0.03, 0.05, 0.99, 0.04),
        }
    )
    client = _FakeEmbeddingClient(mapping)
    usage_records: list = []
    gateway = ModelGateway(client=client, usage_sink=usage_records.append)
    store = InMemoryEmbeddingStore()
    service = EmbeddingService(gateway, store)
    service.index_documents(
        [doc for doc, _ in SEEDED_FTA_FIXTURES],
        source=PromptSource.PUBLIC_SOURCE,
    )
    return service, client, usage_records


def test_gateway_embed_enforces_boundary_redaction_provider_pinning_and_cost_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIP_EMBEDDING_INPUT_USD_PER_MILLION", "0.02")
    client = _FakeEmbeddingClient(
        [
            SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.6, 0.8, 0.0, 0.0])],
                usage=SimpleNamespace(prompt_tokens=250),
            )
        ]
    )
    records = []
    gateway = ModelGateway(client=client, usage_sink=records.append)

    # 1. Prohibited origins are refused before policy or client access (#223).
    with pytest.raises(ProhibitedInputError):
        gateway.embed("crm note", source=PromptSource.CRM_NOTE)
    with pytest.raises(ProhibitedInputError):
        gateway.embed("member row", source=PromptSource.MEMBER_RECORD)
    assert client.calls == []

    # 2. Allowed source redacts PII before calling the embeddings API and logs cost without content.
    result = gateway.embed(
        "Tariff enquiry from exporter@example.test on HS 5101 wool",
        source=PromptSource.PUBLIC_SOURCE,
    )
    assert result.model == DEFAULT_EMBEDDING_MODEL
    assert result.dimensions == 4
    assert result.vector == (0.6, 0.8, 0.0, 0.0)
    assert result.redaction_counts == {"email": 1}
    assert result.input_tokens == 250
    assert result.cost_usd == "0.000005"
    assert result.cost_basis == "configured_token_estimate"
    assert client.calls == [
        {
            "model": DEFAULT_EMBEDDING_MODEL,
            "input": "Tariff enquiry from [redacted:email] on HS 5101 wool",
            "encoding_format": "float",
        }
    ]
    assert len(records) == 1
    serialized_usage = json.dumps(asdict(records[0]))
    assert "exporter@example.test" not in serialized_usage
    assert "HS 5101" not in serialized_usage
    assert records[0].output_tokens == 0

    # 3. Perplexity provider is refused for embeddings rather than silently falling back to OpenAI.
    perplexity_gw = ModelGateway(
        client=client,
        model="sonar",
        provider="perplexity",
        usage_sink=records.append,
    )
    with pytest.raises(GatewayNotConfiguredError, match="SIP_MODEL_PROVIDER=openai"):
        perplexity_gw.embed("wool tariff", source=PromptSource.PUBLIC_SOURCE)


def test_gateway_embed_retries_transient_error_and_validates_vector_shape() -> None:
    records = []
    client = _FakeEmbeddingClient(
        [
            RuntimeError("transient network reset"),
            SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.5, 0.5, 0.5, 0.5])],
                usage=SimpleNamespace(
                    input_tokens=10,
                    cost={"currency": "USD", "total_cost": "0.0001"},
                ),
            ),
        ]
    )
    gateway = ModelGateway(client=client, usage_sink=records.append)
    res = gateway.embed("public trade release", source=PromptSource.PUBLIC_SOURCE)
    assert res.dimensions == 4
    assert res.cost_usd == "0.0001"
    assert res.cost_basis == "provider_reported"
    assert records[0].attempts == 2 and records[0].succeeded is True

    # Exhausted retries record a single failed usage entry and raise GatewayCallError.
    fail_records = []
    fail_client = _FakeEmbeddingClient([RuntimeError("boom"), RuntimeError("boom")])
    with pytest.raises(GatewayCallError, match="2 attempts"):
        ModelGateway(client=fail_client, usage_sink=fail_records.append).embed(
            "public trade release", source=PromptSource.PUBLIC_SOURCE
        )
    assert len(fail_records) == 1 and fail_records[0].succeeded is False

    # Audit failure after a completed provider call raises GatewayAuditError without re-calling.
    single_client = _FakeEmbeddingClient(
        [
            SimpleNamespace(
                data=[SimpleNamespace(embedding=[1.0, 0.0])],
                usage=SimpleNamespace(input_tokens=4),
            )
        ]
    )

    def broken_sink(_u):
        raise RuntimeError("db down")

    with pytest.raises(GatewayAuditError):
        ModelGateway(client=single_client, usage_sink=broken_sink).embed(
            "public trade release", source=PromptSource.PUBLIC_SOURCE
        )
    assert len(single_client.calls) == 1

    # Invalid vector payloads fail closed.
    for bad_payload in (
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[SimpleNamespace(embedding=[])]),
        SimpleNamespace(data=[SimpleNamespace(embedding=[True, 1.0])]),
        SimpleNamespace(data=[SimpleNamespace(embedding=[math.nan, 1.0])]),
        SimpleNamespace(data=[SimpleNamespace(embedding=["0.1", 1.0])]),
    ):
        bad_client = _FakeEmbeddingClient([bad_payload, bad_payload])
        with pytest.raises(GatewayCallError):
            ModelGateway(client=bad_client, usage_sink=lambda _u: None).embed(
                "public trade release", source=PromptSource.PUBLIC_SOURCE
            )


def test_nearest_neighbour_retrieval_ranks_seeded_fixtures_with_thresholds_and_filters() -> None:
    service, _client, usage_records = _seeded_service()

    # 1. Querying for greasy wool duty returns wool fixtures ranked by cosine similarity,
    #    excluding dairy and services which fall below min_score=0.75.
    wool_hits = service.retrieve(
        "fta_corpus",
        "What is the greasy wool duty schedule?",
        source=PromptSource.PUBLIC_SOURCE,
        min_score=0.75,
    )
    assert [hit.record_id for hit in wool_hits] == [
        "FTA-CH2-WOOL-01",
        "FTA-NOTE-COMMENTARY-01",
        "FTA-CH3-ROO-01",
    ]
    assert wool_hits[0].score > wool_hits[1].score > wool_hits[2].score
    assert all(hit.score >= 0.75 for hit in wool_hits)

    # 2. Metadata filter: source_tier=1 restricts results to primary treaty text only.
    tier1_wool = service.retrieve(
        "fta_corpus",
        "What is the greasy wool duty schedule?",
        source=PromptSource.PUBLIC_SOURCE,
        min_score=0.75,
        filters=RetrievalFilters(sector="wool", source_tier=1),
    )
    assert [hit.record_id for hit in tier1_wool] == ["FTA-CH2-WOOL-01"]

    # 3. Metadata filter: max_source_tier=2 includes official + regulatory (tiers 1..2) and drops
    #    tier 3 commentary.
    official_wool = service.retrieve(
        "fta_corpus",
        "What is the greasy wool duty schedule?",
        source=PromptSource.PUBLIC_SOURCE,
        min_score=0.75,
        filters=RetrievalFilters(sector="wool", max_source_tier=2),
    )
    assert [hit.record_id for hit in official_wool] == [
        "FTA-CH2-WOOL-01",
        "FTA-CH3-ROO-01",
    ]

    # 4. Metadata filter by jurisdiction="IN" and sector="services".
    services_hits = service.retrieve(
        "fta_corpus",
        "software visa mobility commitments",
        source=PromptSource.PUBLIC_SOURCE,
        min_score=0.80,
        filters=RetrievalFilters(sector="services", jurisdiction="IN"),
    )
    assert [hit.record_id for hit in services_hits] == ["FTA-CH8-SERVICES-01"]
    assert services_hits[0].score > 0.99

    # Every indexing + query embedding went through ModelGateway and logged usage.
    assert len(usage_records) == len(SEEDED_FTA_FIXTURES) + 4


def test_semantic_candidate_dedupe_detects_cross_run_duplicates_and_excludes_self() -> None:
    mapping = {
        "DGFT notifies zero customs duty on New Zealand greasy wool imports": (
            0.97,
            0.12,
            0.04,
            0.18,
        ),
        "India commerce ministry eliminates tariff on NZ raw wool under FTA": (
            0.96,
            0.14,
            0.05,
            0.19,
        ),
        "Reserve Bank of India holds repo rate unchanged at monetary policy meeting": (
            0.05,
            0.08,
            0.95,
            0.20,
        ),
    }
    client = _FakeEmbeddingClient(mapping)
    gateway = ModelGateway(client=client, usage_sink=lambda _u: None)
    store = InMemoryEmbeddingStore()
    service = EmbeddingService(gateway, store)

    run1_wool = EmbeddingDocument(
        corpus="sip_candidates",
        record_id="cand-run1-001",
        title="DGFT notifies zero customs duty on NZ wool",
        text="DGFT notifies zero customs duty on New Zealand greasy wool imports",
        sector="wool",
        jurisdiction="IN",
        source_tier=1,
    )
    run1_rbi = EmbeddingDocument(
        corpus="sip_candidates",
        record_id="cand-run1-002",
        title="RBI holds repo rate unchanged",
        text="Reserve Bank of India holds repo rate unchanged at monetary policy meeting",
        sector="finance",
        jurisdiction="IN",
        source_tier=1,
    )
    service.index_documents([run1_wool, run1_rbi], source=PromptSource.PUBLIC_SOURCE)

    # Same candidate re-checked against the store never matches itself.
    self_matches = service.find_semantic_duplicates(
        "sip_candidates",
        run1_wool,
        source=PromptSource.PUBLIC_SOURCE,
        threshold=0.85,
    )
    assert self_matches == []

    # Next day's run captures a semantically equivalent announcement from another outlet.
    run2_wool = EmbeddingDocument(
        corpus="sip_candidates",
        record_id="cand-run2-009",
        title="India eliminates tariff on NZ raw wool",
        text="India commerce ministry eliminates tariff on NZ raw wool under FTA",
        sector="wool",
        jurisdiction="IN",
        source_tier=2,
    )
    duplicates = service.find_semantic_duplicates(
        "sip_candidates",
        run2_wool,
        source=PromptSource.PUBLIC_SOURCE,
        threshold=0.90,
        index_after_search=True,
    )
    assert len(duplicates) == 1
    assert duplicates[0].candidate_record_id == "cand-run2-009"
    assert duplicates[0].matched_record_id == "cand-run1-001"
    assert duplicates[0].score > 0.99

    # Because index_after_search=True was set, cand-run2-009 is now stored without a second
    # gateway call.
    stored = store.get(
        "sip_candidates", "cand-run2-009", embedding_model=service.embedding_model
    )
    assert stored is not None
    assert stored.title == "India eliminates tariff on NZ raw wool"


def test_dimension_mismatch_and_validation_guards_fail_closed() -> None:
    store = InMemoryEmbeddingStore()
    row = StoredEmbedding(
        corpus="fta_corpus",
        record_id="rec-1",
        title="Four-dim vector",
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        dimensions=4,
        embedding=(1.0, 0.0, 0.0, 0.0),
        content_sha256="a" * 64,
        sector="wool",
        jurisdiction="NZ",
        source_tier=1,
    )
    store.upsert(row)
    assert store.get("fta_corpus", "rec-1", embedding_model=DEFAULT_EMBEDDING_MODEL) == row

    with pytest.raises(DimensionMismatchError):
        store.search(
            "fta_corpus",
            (1.0, 0.0),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
        )
    with pytest.raises(DimensionMismatchError):
        cosine_similarity((1.0, 0.0), (1.0, 0.0, 0.0))
    assert cosine_similarity((0.0, 0.0), (1.0, 0.0)) == 0.0

    with pytest.raises(ValueError, match="source_tier"):
        EmbeddingDocument(
            corpus="c",
            record_id="r",
            title="t",
            text="x",
            source_tier=6,
        )
    with pytest.raises(ValueError, match="min_score"):
        store.search(
            "fta_corpus",
            (1.0, 0.0, 0.0, 0.0),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            min_score=1.5,
        )
    with pytest.raises(ValueError, match="limit"):
        store.search(
            "fta_corpus",
            (1.0, 0.0, 0.0, 0.0),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            limit=0,
        )
    with pytest.raises(TypeError, match="exclude_record_ids"):
        RetrievalFilters(exclude_record_ids="not-a-tuple")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ModelGateway"):
        EmbeddingService("not-a-gateway", store)  # type: ignore[arg-type]


def test_postgres_store_sql_branches_for_pgvector_and_array_fallback() -> None:
    from services.api.embeddings import PostgresEmbeddingStore

    executed: list[tuple[str, object]] = []

    class FakeCursor:
        def __init__(self, one=None, all_rows=None):
            self._one = one
            self._all = all_rows or []

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def execute(self, sql: str, params: object = None):
            executed.append((sql, params))
            self._one = (1,)

        def fetchone(self):
            return self._one

        def fetchall(self):
            return self._all

    class FakeConn:
        def __init__(self, has_pgvector: bool) -> None:
            self.has_pgvector = has_pgvector
            self.stored_row = (
                "fta_corpus",
                "FTA-CH2-WOOL-01",
                "Wool duty elimination",
                "wool",
                "bilateral",
                1,
                DEFAULT_EMBEDDING_MODEL,
                4,
                [0.98, 0.1, 0.05, 0.15],
                "a" * 64,
            )

        def cursor(self, **_kwargs):
            return FakeCursor(one=(1,))

        def execute(self, sql: str, params: object = None):
            executed.append((sql, params))
            normalized = " ".join(sql.split()).lower()
            if "information_schema.columns" in normalized:
                return FakeCursor(one=(self.has_pgvector,))
            if "dimensions <>" in normalized:
                return FakeCursor(one=None)
            if "select corpus, record_id, title, sector" in normalized:
                return FakeCursor(one=self.stored_row)
            if "order by score desc" in normalized:
                return FakeCursor(
                    all_rows=[
                        (
                            "fta_corpus",
                            "FTA-CH2-WOOL-01",
                            "Wool duty elimination",
                            0.992,
                            "wool",
                            "bilateral",
                            1,
                            DEFAULT_EMBEDDING_MODEL,
                            "a" * 64,
                        )
                    ]
                )
            return FakeCursor()

    row = StoredEmbedding(
        corpus="fta_corpus",
        record_id="FTA-CH2-WOOL-01",
        title="Wool duty elimination",
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        dimensions=4,
        embedding=(0.98, 0.1, 0.05, 0.15),
        content_sha256="a" * 64,
        sector="wool",
        jurisdiction="bilateral",
        source_tier=1,
    )

    for has_pgvector, expected_fragment in (
        (True, "embedding_vec <=> %s::vector"),
        (False, "cosine_similarity(embedding, %s::double precision[])"),
    ):
        executed.clear()
        pg_store = PostgresEmbeddingStore(FakeConn(has_pgvector))  # type: ignore[arg-type]
        pg_store.upsert(row)
        got = pg_store.get("fta_corpus", "FTA-CH2-WOOL-01", embedding_model=DEFAULT_EMBEDDING_MODEL)
        assert got == row
        hits = pg_store.search(
            "fta_corpus",
            (0.99, 0.08, 0.04, 0.12),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            min_score=0.75,
            filters=RetrievalFilters(sector="wool", max_source_tier=2),
        )
        assert len(hits) == 1 and hits[0].record_id == "FTA-CH2-WOOL-01"
        assert any(expected_fragment in sql for sql, _ in executed)

