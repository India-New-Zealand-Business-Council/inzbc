"""Shared vector store and gateway-backed semantic retrieval service (#63).

Backs three platform capabilities through a single server-side implementation:
- **FTA retrieval ranking:** nearest-neighbour search over `corpus="fta_corpus"` with score
  thresholds and sector/jurisdiction filters (advisory capability; does not replace the lexical
  production FTA ranker unless explicitly wired).
- **Cross-run candidate dedupe:** semantic duplicate detection over `corpus="sip_candidates"`
  with configurable cosine-similarity thresholds and self-exclusion.
- **Source discovery:** nearest-neighbour lookup over `corpus="source_library"` filtered by
  `jurisdiction`, `sector`, and `source_tier` (`1..5`).

Every embedding is generated server-side through `ModelGateway.embed(text, source=...)`, which
enforces `PromptSource` boundary refusal (#223), regex redaction (#37), provider pinning (`openai`),
and content-free `ModelUsage` cost/audit logging (#36) before any vector is stored or queried.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

import psycopg

from services.api.audit import record_audit
from services.api.model_gateway import ModelGateway
from services.api.prompt_boundary import PromptSource


class DimensionMismatchError(ValueError):
    """Query vector dimensions do not match the stored embedding dimensions for the model."""


def _require_non_blank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _validate_source_tier(value: int | None, field_name: str = "source_tier") -> int | None:
    if value is None:
        return None
    if type(value) is not int or not (1 <= value <= 5):
        raise ValueError(f"{field_name} must be an integer between 1 and 5")
    return value


def _validate_vector(vector: Sequence[float], field_name: str = "embedding") -> tuple[float, ...]:
    if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)) or len(vector) == 0:
        raise ValueError(f"{field_name} must be a non-empty numeric sequence")
    cleaned: list[float] = []
    for item in vector:
        if type(item) not in {int, float} or not math.isfinite(float(item)):
            raise ValueError(f"{field_name} contains a non-finite or non-numeric value")
        cleaned.append(float(item))
    return tuple(cleaned)


def _validate_score_threshold(value: float, field_name: str = "min_score") -> float:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be a finite number between -1.0 and 1.0")
    score = float(value)
    if not (-1.0 <= score <= 1.0):
        raise ValueError(f"{field_name} must be between -1.0 and 1.0, got {score}")
    return score


def _validate_limit(limit: int) -> int:
    if type(limit) is not int or not (1 <= limit <= 200):
        raise ValueError("limit must be an integer between 1 and 200")
    return limit


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Exact cosine similarity matching the SQL `cosine_similarity` function in `schema.sql`."""
    vec_a = _validate_vector(a, "a")
    vec_b = _validate_vector(b, "b")
    if len(vec_a) != len(vec_b):
        raise DimensionMismatchError(
            f"embedding dimension mismatch: {len(vec_a)} != {len(vec_b)}"
        )
    dot = sum(x * y for x, y in zip(vec_a, vec_b, strict=True))
    norm_a = sum(x * x for x in vec_a)
    norm_b = sum(y * y for y in vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


@dataclass(frozen=True)
class EmbeddingDocument:
    """One document or candidate item to embed and index through the gateway."""

    corpus: str
    record_id: str
    title: str
    text: str
    sector: str | None = None
    jurisdiction: str | None = None
    source_tier: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "corpus", _require_non_blank(self.corpus, "corpus"))
        object.__setattr__(self, "record_id", _require_non_blank(self.record_id, "record_id"))
        object.__setattr__(self, "title", _require_non_blank(self.title, "title"))
        object.__setattr__(self, "text", _require_non_blank(self.text, "text"))
        if self.sector is not None:
            object.__setattr__(self, "sector", _require_non_blank(self.sector, "sector"))
        if self.jurisdiction is not None:
            object.__setattr__(
                self, "jurisdiction", _require_non_blank(self.jurisdiction, "jurisdiction")
            )
        _validate_source_tier(self.source_tier, "source_tier")


@dataclass(frozen=True)
class RetrievalFilters:
    """Metadata filters applied during nearest-neighbour retrieval."""

    sector: str | None = None
    jurisdiction: str | None = None
    source_tier: int | None = None
    max_source_tier: int | None = None
    exclude_record_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.sector is not None:
            object.__setattr__(self, "sector", _require_non_blank(self.sector, "sector"))
        if self.jurisdiction is not None:
            object.__setattr__(
                self, "jurisdiction", _require_non_blank(self.jurisdiction, "jurisdiction")
            )
        _validate_source_tier(self.source_tier, "source_tier")
        _validate_source_tier(self.max_source_tier, "max_source_tier")
        if isinstance(self.exclude_record_ids, (str, bytes)) or not isinstance(
            self.exclude_record_ids, Iterable
        ):
            raise TypeError("exclude_record_ids must be an iterable of record_id strings")
        cleaned_excluded = tuple(
            _require_non_blank(item, "exclude_record_ids item")
            for item in self.exclude_record_ids
        )
        object.__setattr__(self, "exclude_record_ids", cleaned_excluded)


@dataclass(frozen=True)
class StoredEmbedding:
    """One persisted embedding row in `semantic_embeddings`."""

    corpus: str
    record_id: str
    title: str
    embedding_model: str
    dimensions: int
    embedding: tuple[float, ...]
    content_sha256: str
    sector: str | None = None
    jurisdiction: str | None = None
    source_tier: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "corpus", _require_non_blank(self.corpus, "corpus"))
        object.__setattr__(self, "record_id", _require_non_blank(self.record_id, "record_id"))
        object.__setattr__(self, "title", _require_non_blank(self.title, "title"))
        object.__setattr__(
            self, "embedding_model", _require_non_blank(self.embedding_model, "embedding_model")
        )
        object.__setattr__(
            self, "content_sha256", _require_non_blank(self.content_sha256, "content_sha256")
        )
        vec = _validate_vector(self.embedding, "embedding")
        object.__setattr__(self, "embedding", vec)
        if type(self.dimensions) is not int or self.dimensions != len(vec):
            raise ValueError(
                f"dimensions ({self.dimensions}) must match len(embedding) ({len(vec)})"
            )
        if self.sector is not None:
            object.__setattr__(self, "sector", _require_non_blank(self.sector, "sector"))
        if self.jurisdiction is not None:
            object.__setattr__(
                self, "jurisdiction", _require_non_blank(self.jurisdiction, "jurisdiction")
            )
        _validate_source_tier(self.source_tier, "source_tier")


@dataclass(frozen=True)
class RetrievalHit:
    """One ranked nearest-neighbour hit returned by semantic search."""

    corpus: str
    record_id: str
    title: str
    score: float
    sector: str | None = None
    jurisdiction: str | None = None
    source_tier: int | None = None
    embedding_model: str = ""
    content_sha256: str = ""


@dataclass(frozen=True)
class DuplicateMatch:
    """One near-duplicate candidate match returned by `find_semantic_duplicates`."""

    candidate_record_id: str
    matched_record_id: str
    matched_title: str
    score: float
    sector: str | None = None
    jurisdiction: str | None = None
    source_tier: int | None = None


class EmbeddingStore(Protocol):
    """Protocol implemented by both `InMemoryEmbeddingStore` and `PostgresEmbeddingStore`."""

    def upsert(self, record: StoredEmbedding) -> StoredEmbedding: ...

    def get(
        self, corpus: str, record_id: str, *, embedding_model: str
    ) -> StoredEmbedding | None: ...

    def search(
        self,
        corpus: str,
        query_vector: Sequence[float],
        *,
        embedding_model: str,
        min_score: float = 0.70,
        limit: int = 10,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalHit]: ...


class InMemoryEmbeddingStore:
    """Deterministic in-memory vector store for unit tests and offline evaluation fixtures."""

    def __init__(self, initial: Iterable[StoredEmbedding] = ()) -> None:
        self._rows: dict[tuple[str, str, str], StoredEmbedding] = {}
        for item in initial:
            self.upsert(item)

    def upsert(self, record: StoredEmbedding) -> StoredEmbedding:
        if type(record) is not StoredEmbedding:
            raise TypeError("record must be a StoredEmbedding instance")
        key = (record.corpus, record.record_id, record.embedding_model)
        self._rows[key] = record
        return record

    def get(
        self, corpus: str, record_id: str, *, embedding_model: str
    ) -> StoredEmbedding | None:
        key = (
            _require_non_blank(corpus, "corpus"),
            _require_non_blank(record_id, "record_id"),
            _require_non_blank(embedding_model, "embedding_model"),
        )
        return self._rows.get(key)

    def search(
        self,
        corpus: str,
        query_vector: Sequence[float],
        *,
        embedding_model: str,
        min_score: float = 0.70,
        limit: int = 10,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalHit]:
        clean_corpus = _require_non_blank(corpus, "corpus")
        clean_model = _require_non_blank(embedding_model, "embedding_model")
        vec = _validate_vector(query_vector, "query_vector")
        threshold = _validate_score_threshold(min_score, "min_score")
        clean_limit = _validate_limit(limit)
        active_filters = filters or RetrievalFilters()
        if type(active_filters) is not RetrievalFilters:
            raise TypeError("filters must be a RetrievalFilters instance")

        excluded = set(active_filters.exclude_record_ids)
        hits: list[RetrievalHit] = []
        for row in self._rows.values():
            if row.corpus != clean_corpus or row.embedding_model != clean_model:
                continue
            if row.dimensions != len(vec):
                raise DimensionMismatchError(
                    f"stored record {row.record_id!r} has {row.dimensions} dimensions, "
                    f"query has {len(vec)}"
                )
            if row.record_id in excluded:
                continue
            if active_filters.sector is not None and row.sector != active_filters.sector:
                continue
            if (
                active_filters.jurisdiction is not None
                and row.jurisdiction != active_filters.jurisdiction
            ):
                continue
            if (
                active_filters.source_tier is not None
                and row.source_tier != active_filters.source_tier
            ):
                continue
            if active_filters.max_source_tier is not None and (
                row.source_tier is None or row.source_tier > active_filters.max_source_tier
            ):
                continue
            score = cosine_similarity(row.embedding, vec)
            if score >= threshold:
                hits.append(
                    RetrievalHit(
                        corpus=row.corpus,
                        record_id=row.record_id,
                        title=row.title,
                        score=score,
                        sector=row.sector,
                        jurisdiction=row.jurisdiction,
                        source_tier=row.source_tier,
                        embedding_model=row.embedding_model,
                        content_sha256=row.content_sha256,
                    )
                )

        hits.sort(key=lambda h: (-h.score, h.record_id))
        return hits[:clean_limit]


class PostgresEmbeddingStore:
    """Postgres-backed vector store over `semantic_embeddings` (`database/schema.sql`).

    Automatically uses pgvector's `<=>` cosine-distance operator on `embedding_vec` when the
    `vector` extension is installed on the Postgres host, and falls back to the SQL
    `cosine_similarity(embedding, query::double precision[])` function on a stock Postgres
    instance so CI and local databases produce identical results.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        self._has_pgvector_column: bool | None = None

    def _uses_pgvector(self) -> bool:
        if self._has_pgvector_column is None:
            row = self._conn.execute(
                "select exists ("
                "  select 1 from information_schema.columns "
                "  where table_schema = 'public' "
                "    and table_name = 'semantic_embeddings' "
                "    and column_name = 'embedding_vec'"
                ")"
            ).fetchone()
            self._has_pgvector_column = bool(row and row[0])
        return self._has_pgvector_column

    def upsert(self, record: StoredEmbedding) -> StoredEmbedding:
        if type(record) is not StoredEmbedding:
            raise TypeError("record must be a StoredEmbedding instance")
        self._conn.execute(
            """
            insert into semantic_embeddings (
              corpus, record_id, title, sector, jurisdiction, source_tier,
              embedding_model, dimensions, embedding, content_sha256, updated_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            on conflict (corpus, record_id, embedding_model) do update set
              title          = excluded.title,
              sector         = excluded.sector,
              jurisdiction   = excluded.jurisdiction,
              source_tier    = excluded.source_tier,
              dimensions     = excluded.dimensions,
              embedding      = excluded.embedding,
              content_sha256 = excluded.content_sha256,
              updated_at     = now()
            """,
            (
                record.corpus,
                record.record_id,
                record.title,
                record.sector,
                record.jurisdiction,
                record.source_tier,
                record.embedding_model,
                record.dimensions,
                list(record.embedding),
                record.content_sha256,
            ),
        )
        record_audit(
            self._conn,
            action="embedding.upsert",
            record_type="semantic_embeddings",
            record_id=f"{record.corpus}:{record.record_id}",
            new_value=json.dumps(
                {
                    "corpus": record.corpus,
                    "record_id": record.record_id,
                    "embedding_model": record.embedding_model,
                    "dimensions": record.dimensions,
                    "content_sha256": record.content_sha256,
                },
                sort_keys=True,
            ),
        )
        return record

    def get(
        self, corpus: str, record_id: str, *, embedding_model: str
    ) -> StoredEmbedding | None:
        clean_corpus = _require_non_blank(corpus, "corpus")
        clean_record_id = _require_non_blank(record_id, "record_id")
        clean_model = _require_non_blank(embedding_model, "embedding_model")
        row = self._conn.execute(
            """
            select corpus, record_id, title, sector, jurisdiction, source_tier,
                   embedding_model, dimensions, embedding, content_sha256
            from semantic_embeddings
            where corpus = %s and record_id = %s and embedding_model = %s
            """,
            (clean_corpus, clean_record_id, clean_model),
        ).fetchone()
        if row is None:
            return None
        return StoredEmbedding(
            corpus=row[0],
            record_id=row[1],
            title=row[2],
            sector=row[3],
            jurisdiction=row[4],
            source_tier=row[5],
            embedding_model=row[6],
            dimensions=row[7],
            embedding=tuple(float(v) for v in row[8]),
            content_sha256=row[9],
        )

    def search(
        self,
        corpus: str,
        query_vector: Sequence[float],
        *,
        embedding_model: str,
        min_score: float = 0.70,
        limit: int = 10,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalHit]:
        clean_corpus = _require_non_blank(corpus, "corpus")
        clean_model = _require_non_blank(embedding_model, "embedding_model")
        vec = _validate_vector(query_vector, "query_vector")
        threshold = _validate_score_threshold(min_score, "min_score")
        clean_limit = _validate_limit(limit)
        active_filters = filters or RetrievalFilters()
        if type(active_filters) is not RetrievalFilters:
            raise TypeError("filters must be a RetrievalFilters instance")

        mismatch = self._conn.execute(
            """
            select record_id, dimensions
            from semantic_embeddings
            where corpus = %s and embedding_model = %s and dimensions <> %s
            limit 1
            """,
            (clean_corpus, clean_model, len(vec)),
        ).fetchone()
        if mismatch is not None:
            raise DimensionMismatchError(
                f"stored record {mismatch[0]!r} has {mismatch[1]} dimensions, "
                f"query has {len(vec)}"
            )

        if self._uses_pgvector():
            vec_literal = "[" + ",".join(repr(float(x)) for x in vec) + "]"
            score_expr = "1.0 - (embedding_vec <=> %s::vector)"
            score_param: object = vec_literal
        else:
            score_expr = "cosine_similarity(embedding, %s::double precision[])"
            score_param = list(vec)

        excluded = list(active_filters.exclude_record_ids)
        rows = self._conn.execute(
            f"""
            select corpus, record_id, title, score, sector, jurisdiction,
                   source_tier, embedding_model, content_sha256
            from (
              select
                corpus,
                record_id,
                title,
                {score_expr} as score,
                sector,
                jurisdiction,
                source_tier,
                embedding_model,
                content_sha256
              from semantic_embeddings
              where corpus = %s
                and embedding_model = %s
                and dimensions = %s
                and (%s::text is null or sector = %s)
                and (%s::text is null or jurisdiction = %s)
                and (%s::smallint is null or source_tier = %s)
                and (
                  %s::smallint is null
                  or (source_tier is not null and source_tier <= %s)
                )
                and not (record_id = any(%s::text[]))
            ) as scored
            where score is not null and score >= %s
            order by score desc, record_id asc
            limit %s
            """,
            (
                score_param,
                clean_corpus,
                clean_model,
                len(vec),
                active_filters.sector,
                active_filters.sector,
                active_filters.jurisdiction,
                active_filters.jurisdiction,
                active_filters.source_tier,
                active_filters.source_tier,
                active_filters.max_source_tier,
                active_filters.max_source_tier,
                excluded,
                threshold,
                clean_limit,
            ),
        ).fetchall()

        return [
            RetrievalHit(
                corpus=row[0],
                record_id=row[1],
                title=row[2],
                score=float(row[3]),
                sector=row[4],
                jurisdiction=row[5],
                source_tier=row[6],
                embedding_model=row[7],
                content_sha256=row[8],
            )
            for row in rows
        ]


class EmbeddingService:
    """Server-side semantic indexing, nearest-neighbour retrieval, and candidate dedupe (#63).

    All embeddings are generated through `ModelGateway.embed(text, source=source)` — never through
    a direct provider client — so prompt-boundary checks, regex redaction, provider pinning, and
    audit/cost logging cannot be bypassed.
    """

    def __init__(self, gateway: ModelGateway, store: EmbeddingStore) -> None:
        if type(gateway) is not ModelGateway:
            raise TypeError("gateway must be an exact ModelGateway instance")
        self._gateway = gateway
        self._store = store

    @property
    def embedding_model(self) -> str:
        return self._gateway.embedding_model

    def index_document(
        self, doc: EmbeddingDocument, *, source: PromptSource
    ) -> StoredEmbedding:
        """Embed `doc.text` through the gateway and upsert into the backing vector store."""
        if type(doc) is not EmbeddingDocument:
            raise TypeError("doc must be an EmbeddingDocument instance")
        result = self._gateway.embed(doc.text, source=source)
        digest = hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
        stored = StoredEmbedding(
            corpus=doc.corpus,
            record_id=doc.record_id,
            title=doc.title,
            sector=doc.sector,
            jurisdiction=doc.jurisdiction,
            source_tier=doc.source_tier,
            embedding_model=result.model,
            dimensions=result.dimensions,
            embedding=result.vector,
            content_sha256=digest,
        )
        return self._store.upsert(stored)

    def index_documents(
        self, docs: Iterable[EmbeddingDocument], *, source: PromptSource
    ) -> list[StoredEmbedding]:
        """Embed and upsert a sequence of documents through the gateway."""
        return [self.index_document(doc, source=source) for doc in docs]

    def retrieve(
        self,
        corpus: str,
        query: str,
        *,
        source: PromptSource,
        min_score: float = 0.70,
        limit: int = 10,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalHit]:
        """Embed `query` through the gateway and return ranked hits meeting `min_score` and
        `filters`.
        """
        clean_query = _require_non_blank(query, "query")
        threshold = _validate_score_threshold(min_score, "min_score")
        clean_limit = _validate_limit(limit)
        result = self._gateway.embed(clean_query, source=source)
        return self._store.search(
            corpus,
            result.vector,
            embedding_model=result.model,
            min_score=threshold,
            limit=clean_limit,
            filters=filters,
        )

    def find_semantic_duplicates(
        self,
        corpus: str,
        doc: EmbeddingDocument,
        *,
        source: PromptSource,
        threshold: float = 0.85,
        limit: int = 5,
        filters: RetrievalFilters | None = None,
        index_after_search: bool = False,
    ) -> list[DuplicateMatch]:
        """Check `corpus` for existing items whose cosine similarity to `doc` is `>= threshold`.

        Automatically excludes `doc.record_id` so a re-evaluated candidate never matches itself.
        When `index_after_search=True`, upserts `doc`'s embedding after searching (reusing the
        already-computed gateway vector rather than calling the provider twice).
        """
        if type(doc) is not EmbeddingDocument:
            raise TypeError("doc must be an EmbeddingDocument instance")
        clean_threshold = _validate_score_threshold(threshold, "threshold")
        clean_limit = _validate_limit(limit)

        base_filters = filters or RetrievalFilters()
        if type(base_filters) is not RetrievalFilters:
            raise TypeError("filters must be a RetrievalFilters instance")
        merged_excluded = tuple(
            dict.fromkeys((*base_filters.exclude_record_ids, doc.record_id))
        )
        effective_filters = RetrievalFilters(
            sector=base_filters.sector,
            jurisdiction=base_filters.jurisdiction,
            source_tier=base_filters.source_tier,
            max_source_tier=base_filters.max_source_tier,
            exclude_record_ids=merged_excluded,
        )

        result = self._gateway.embed(doc.text, source=source)
        hits = self._store.search(
            corpus,
            result.vector,
            embedding_model=result.model,
            min_score=clean_threshold,
            limit=clean_limit,
            filters=effective_filters,
        )
        if index_after_search:
            digest = hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
            self._store.upsert(
                StoredEmbedding(
                    corpus=doc.corpus,
                    record_id=doc.record_id,
                    title=doc.title,
                    sector=doc.sector,
                    jurisdiction=doc.jurisdiction,
                    source_tier=doc.source_tier,
                    embedding_model=result.model,
                    dimensions=result.dimensions,
                    embedding=result.vector,
                    content_sha256=digest,
                )
            )
        return [
            DuplicateMatch(
                candidate_record_id=doc.record_id,
                matched_record_id=hit.record_id,
                matched_title=hit.title,
                score=hit.score,
                sector=hit.sector,
                jurisdiction=hit.jurisdiction,
                source_tier=hit.source_tier,
            )
            for hit in hits
        ]


__all__ = [
    "DimensionMismatchError",
    "DuplicateMatch",
    "EmbeddingDocument",
    "EmbeddingService",
    "EmbeddingStore",
    "InMemoryEmbeddingStore",
    "PostgresEmbeddingStore",
    "RetrievalFilters",
    "RetrievalHit",
    "StoredEmbedding",
    "cosine_similarity",
]
