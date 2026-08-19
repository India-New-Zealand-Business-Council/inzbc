"""Postgres persistence for the approved facts library (#188).

The Explainer, Digest and Comms Assistant each draw statistics and statements from their own
corner of the codebase, with no rule stopping the same fact appearing with two different values in
two places - which has already happened once on the homepage. This module is the single write path
for a fact's lifecycle: drafted, approved by someone other than the drafter, and eventually
archived when superseded.

`fact_key` groups every revision of "the same fact" (a stable identifier such as
`FTA-TARIFF-WOOL`, not the row id). `supersedes_id` chains revisions the same way
`decision_records.supersedes_id` does: a correction is a new row pointing at the one it replaces,
never an update to the row itself, so a caller that logged "the tariff is X, approved 3 Aug" can
never have that statement silently become false underneath it.

Self-approval is refused at both layers: the schema's own CHECK constraint
(`approved_by <> created_by`) is the floor, and `approve()` raises before the insert even reaches
the database, so the caller gets a clear error rather than a constraint-violation traceback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from services.api.audit import record_audit

_FACT_COLUMNS = (
    "id, fact_key, content, owner_id, owner_text, status, source, verified_at, "
    "review_due_at, version, supersedes_id, created_by, created_at, approved_by, "
    "approved_at, archived_at"
)


def _iso(value):
    return value.isoformat() if value is not None else None


@dataclass(frozen=True)
class FactRecord:
    id: str
    fact_key: str
    content: str
    owner_id: str | None
    owner_text: str | None
    status: str
    source: str
    verified_at: str | None
    review_due_at: str | None
    version: int
    supersedes_id: str | None
    created_by: str
    created_at: str
    approved_by: str | None
    approved_at: str | None
    archived_at: str | None


def _row_to_record(row: dict) -> FactRecord:
    return FactRecord(
        id=str(row["id"]),
        fact_key=row["fact_key"],
        content=row["content"],
        owner_id=str(row["owner_id"]) if row["owner_id"] else None,
        owner_text=row["owner_text"],
        status=row["status"],
        source=row["source"],
        verified_at=_iso(row["verified_at"]),
        review_due_at=_iso(row["review_due_at"]),
        version=row["version"],
        supersedes_id=str(row["supersedes_id"]) if row["supersedes_id"] else None,
        created_by=str(row["created_by"]),
        created_at=_iso(row["created_at"]),
        approved_by=str(row["approved_by"]) if row["approved_by"] else None,
        approved_at=_iso(row["approved_at"]),
        archived_at=_iso(row["archived_at"]),
    )


class SelfApprovalError(ValueError):
    """Raised when the actor approving a fact is the same actor who drafted it."""


class FactRepository:
    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def draft(
        self,
        fact_key: str,
        content: str,
        source: str,
        *,
        actor_id: str,
        owner_id: str | None = None,
        owner_text: str | None = None,
        verified_at: str | None = None,
        review_due_at: str | None = None,
        supersedes_id: str | None = None,
    ) -> FactRecord:
        """Creates a new draft. If `supersedes_id` is given, the new row's `version` is the
        superseded row's `version + 1`; otherwise this is the fact's first revision (version 1).
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            version = 1
            if supersedes_id is not None:
                prior = conn.execute(
                    "select version from approved_facts where id = %s", (supersedes_id,)
                ).fetchone()
                if prior is None:
                    raise KeyError(f"no fact {supersedes_id!r} to supersede")
                version = prior["version"] + 1

            row = conn.execute(
                "insert into approved_facts (fact_key, content, owner_id, owner_text, status, "
                "source, verified_at, review_due_at, version, supersedes_id, created_by) "
                "values (%s, %s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s) "
                f"returning {_FACT_COLUMNS}",
                (
                    fact_key,
                    content,
                    owner_id,
                    owner_text,
                    source,
                    verified_at,
                    review_due_at,
                    version,
                    supersedes_id,
                    actor_id,
                ),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="approved_fact.draft",
                record_type="approved_facts",
                record_id=str(row["id"]),
                new_value="draft",
                reason=f"{fact_key} v{version}",
            )
            conn.commit()
        return _row_to_record(row)

    def approve(self, fact_id: str, *, actor_id: str) -> FactRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = conn.execute(
                "select status, created_by from approved_facts where id = %s for update",
                (fact_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"no fact {fact_id!r}")
            if str(current["created_by"]) == actor_id:
                raise SelfApprovalError(
                    f"actor {actor_id!r} drafted fact {fact_id!r} and cannot approve it"
                )
            if current["status"] != "draft":
                raise ValueError(
                    f"fact {fact_id!r} is {current['status']!r}, only a draft can be approved"
                )

            row = conn.execute(
                "update approved_facts set status = 'approved', approved_by = %s, "
                "approved_at = now() where id = %s "
                f"returning {_FACT_COLUMNS}",
                (actor_id, fact_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="approved_fact.approve",
                record_type="approved_facts",
                record_id=fact_id,
                old_value="draft",
                new_value="approved",
            )
            conn.commit()
        return _row_to_record(row)

    def archive(self, fact_id: str, *, actor_id: str) -> FactRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = conn.execute(
                "select status from approved_facts where id = %s for update", (fact_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"no fact {fact_id!r}")

            row = conn.execute(
                "update approved_facts set status = 'archived', archived_at = now() "
                f"where id = %s returning {_FACT_COLUMNS}",
                (fact_id,),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="approved_fact.archive",
                record_type="approved_facts",
                record_id=fact_id,
                old_value=current["status"],
                new_value="archived",
            )
            conn.commit()
        return _row_to_record(row)

    def get(self, fact_id: str) -> FactRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_FACT_COLUMNS} from approved_facts where id = %s", (fact_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no fact {fact_id!r}")
        return _row_to_record(row)

    def get_latest_approved(self, fact_key: str) -> FactRecord | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_FACT_COLUMNS} from approved_facts "
                "where fact_key = %s and status = 'approved' "
                "order by version desc limit 1",
                (fact_key,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def history(self, fact_key: str) -> list[FactRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_FACT_COLUMNS} from approved_facts "
                "where fact_key = %s order by version desc",
                (fact_key,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def get_fact_repository() -> FactRepository:
    return FactRepository()
