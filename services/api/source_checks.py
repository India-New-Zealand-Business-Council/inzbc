"""`/api/runs/{run_id}/source-checks` (#55): SIP-184 step 4, per-source outcome recording.

`schemas/api-contract.md` names these routes (`POST`/`GET .../source-checks`) and
`SipPipelineClient.record_source_check`/`list_source_checks` already call them, but nothing in
`services/api` implemented either - found while building the #55 dry run: `source_register.py`
could resolve a SIP-185 code to a `source_library` id (once seeded) but had nowhere to actually
write the outcome. `source_checks.unique(run_id, source_id)` (`database/schema.sql`) is the
mandatory-source coverage gate's real enforcement point: a second POST for the same run+source
must update the existing row, not create a conflicting one, since a source can legitimately be
re-checked after a fallback attempt.

No `actor_id`/audit here, unlike `candidates.py`'s commands: `source_checks` has no owner-facing
decision to audit - it is a mechanical record of what was tried, not a human call. If that
changes, add it the same way `candidate_persistence.py`'s `capture()` does.

**Decision on the upsert (raised in #264 review):** a re-check after a fallback attempt updates
the existing `(run_id, source_id)` row rather than appending a new one, so only the *last* attempt
survives - earlier fallback attempts are not individually retained. This is a deliberate choice,
not an oversight: `record_source_outcome`'s `fallback_attempts` trail already folds the full
attempt sequence into `notes` before this ever gets called, so the row's `notes` field carries
that history even though the row itself doesn't. If per-attempt rows become required as separate
audit evidence, that needs an append-only attempt table - not assumed here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from fastapi import APIRouter, Depends
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict

from apps.sip.pipeline.models import SourceOutcome

router = APIRouter(prefix="/api/runs", tags=["Source checks"])

_SELECT_COLUMNS = (
    "id, run_id, source_id, outcome, checked_at, method, fallback_used, access_error, notes"
)


@dataclass(frozen=True)
class SourceCheckRecord:
    id: str
    run_id: str
    source_id: str
    outcome: SourceOutcome
    checked_at: str
    method: str | None
    fallback_used: bool
    access_error: str | None
    notes: str | None


def _row_to_record(row: dict) -> SourceCheckRecord:
    return SourceCheckRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        source_id=str(row["source_id"]),
        outcome=SourceOutcome(row["outcome"]),
        checked_at=row["checked_at"].isoformat(),
        method=row["method"],
        fallback_used=row["fallback_used"],
        access_error=row["access_error"],
        notes=row["notes"],
    )


class SourceCheckRepository:
    """Postgres-backed persistence for `source_checks`.

    `record()` upserts on `(run_id, source_id)` - the schema's own unique constraint - so a
    source re-checked after a fallback attempt updates the same row instead of colliding with it.
    No optimistic concurrency here: unlike `runs`/`candidates`, there is no multi-step human
    workflow racing to update one source check, just one operator recording what they found.
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def record(
        self,
        run_id: str,
        source_id: str,
        outcome: SourceOutcome,
        method: str | None,
        fallback_used: bool,
        access_error: str | None,
        notes: str | None,
    ) -> SourceCheckRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into source_checks (run_id, source_id, outcome, method, fallback_used, "
                "access_error, notes) values (%s, %s, %s, %s, %s, %s, %s) "
                "on conflict (run_id, source_id) do update set "
                "outcome = excluded.outcome, method = excluded.method, "
                "fallback_used = excluded.fallback_used, access_error = excluded.access_error, "
                "notes = excluded.notes, checked_at = now() "
                f"returning {_SELECT_COLUMNS}",
                (run_id, source_id, outcome.value, method, fallback_used, access_error, notes),
            ).fetchone()
            conn.commit()
        return _row_to_record(row)

    def list_for_run(self, run_id: str) -> list[SourceCheckRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_SELECT_COLUMNS} from source_checks where run_id = %s", (run_id,)
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def get_source_check_repository() -> SourceCheckRepository:
    """FastAPI dependency, overridden in tests - same reasoning as `services/api/runs.py`'s
    `get_run_repository`.
    """
    return SourceCheckRepository()


class SourceCheckOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    source_id: str
    outcome: SourceOutcome
    checked_at: str
    method: str | None
    fallback_used: bool
    access_error: str | None
    notes: str | None


def _out(record: SourceCheckRecord) -> SourceCheckOut:
    return SourceCheckOut(
        id=record.id,
        run_id=record.run_id,
        source_id=record.source_id,
        outcome=record.outcome,
        checked_at=record.checked_at,
        method=record.method,
        fallback_used=record.fallback_used,
        access_error=record.access_error,
        notes=record.notes,
    )


class RecordSourceCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    outcome: SourceOutcome
    method: str | None = None
    fallback_used: bool = False
    access_error: str | None = None
    notes: str | None = None


@router.post(
    "/{run_id}/source-checks", response_model=SourceCheckOut, status_code=201
)
def record_source_check(
    run_id: str,
    body: RecordSourceCheckIn,
    repo: SourceCheckRepository = Depends(get_source_check_repository),
) -> SourceCheckOut:
    return _out(
        repo.record(
            run_id=run_id,
            source_id=body.source_id,
            outcome=body.outcome,
            method=body.method,
            fallback_used=body.fallback_used,
            access_error=body.access_error,
            notes=body.notes,
        )
    )


@router.get("/{run_id}/source-checks", response_model=list[SourceCheckOut])
def list_source_checks(
    run_id: str, repo: SourceCheckRepository = Depends(get_source_check_repository)
) -> list[SourceCheckOut]:
    return [_out(record) for record in repo.list_for_run(run_id)]
