"""`/api/runs/{run_id}/authorisations` (#55): recording launch and resumption authority.

`run_authorisations` (#227) gives `RunRepository.apply_transition` somewhere durable to check
`Draft -> Run Authorised` and `Paused -> Coverage Locked` against, and `apply_transition` itself
has enforced that since #227 landed. But nothing ever wrote to the table: #227 built the home,
#120 built the transition endpoints that read it, and neither built the endpoint that inserts a
row - so a real client can authenticate, hold every role, and still never legally get a run past
Draft, because there is no way to obtain an `approval_ref` that `apply_transition` will accept.
Found while assembling #55's end-to-end evidence: `run_dry_run.py` sidesteps this on purpose (it
is *unauthorised* by design), so nothing else in the codebase had reason to notice the gap.

**Who may authorise.** There is no `run_authorisation_role_permissions` config table the way
`decision_role_permissions` gates the three ADR-0005 decision kinds - this table's FK only proves
the actor held *some* role, not that the role is the right one for this act. Restricted here to
SIP Owner for both Launch and Resumption, matching the weight `decision_role_permissions`
(migration 0003) already gives CEO Ruling: authorising a run to start, or resume after a pause, is
the same order of accountability as ruling on its outcome. If INZBC wants this split further
(e.g. a Secretariat launch with SIP Owner resumption), that is a configuration decision for a
follow-up, not a judgement call to make silently here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.api.auth import SIP_OWNER, STAFF_READ, Principal
from services.api.decisions import DecisionNotPermittedError, ReportRepository
from services.api.session import AUTH_RESPONSES, read_access, write_access

router = APIRouter(prefix="/api/runs", tags=["Run authorisations"], responses=AUTH_RESPONSES)

_CLOCK_SKEW_ALLOWANCE = timedelta(minutes=5)

_SELECT_COLUMNS = (
    "id, run_id, kind, actor_id, decided_at, recorded_at, reason, evidence_ref"
)


@dataclass(frozen=True)
class RunAuthorisationRecord:
    id: str
    run_id: str
    kind: str
    actor_id: str
    decided_at: str
    recorded_at: str
    reason: str
    evidence_ref: str


def _row_to_record(row: dict) -> RunAuthorisationRecord:
    return RunAuthorisationRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        kind=row["kind"],
        actor_id=str(row["actor_id"]),
        decided_at=row["decided_at"].isoformat(),
        recorded_at=row["recorded_at"].isoformat(),
        reason=row["reason"],
        evidence_ref=row["evidence_ref"],
    )


class RunAuthorisationRepository:
    """Postgres-backed persistence for `run_authorisations`. Append-only at the database level
    (`database/schema.sql`'s `run_authorisations_append_only` trigger) - there is deliberately no
    update or delete method here to match.
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def authorise(
        self,
        run_id: str,
        kind: str,
        *,
        actor_id: str,
        reason: str,
        evidence_ref: str,
        decided_at: datetime,
    ) -> RunAuthorisationRecord:
        """Records one authorisation and returns it, for use as `approval_ref` on
        `RunRepository.apply_transition`.

        Resolves the actor's role via `ReportRepository.role_id_for` rather than duplicating that
        lookup - one place decides "which role was this act performed in" for every act that
        needs the answer, the same reasoning that method's own docstring gives for reusing it
        instead of re-resolving the role inline.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn, conn.transaction():
            actor_role_id = ReportRepository(self._database_url).role_id_for(
                actor_id, (SIP_OWNER,)
            )
            row = conn.execute(
                "insert into run_authorisations (run_id, kind, actor_id, actor_role_id, "
                "decided_at, reason, evidence_ref) values (%s, %s, %s, %s, %s, %s, %s) "
                f"returning {_SELECT_COLUMNS}",
                (run_id, kind, actor_id, actor_role_id, decided_at, reason, evidence_ref),
            ).fetchone()
        return _row_to_record(row)

    def list_for_run(self, run_id: str) -> list[RunAuthorisationRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_SELECT_COLUMNS} from run_authorisations where run_id = %s "
                "order by recorded_at",
                (run_id,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def get_run_authorisation_repository() -> RunAuthorisationRepository:
    return RunAuthorisationRepository()


class RunAuthorisationOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    kind: str
    actor_id: str
    decided_at: str
    recorded_at: str
    reason: str
    evidence_ref: str


def _out(record: RunAuthorisationRecord) -> RunAuthorisationOut:
    return RunAuthorisationOut(
        id=record.id,
        run_id=record.run_id,
        kind=record.kind,
        actor_id=record.actor_id,
        decided_at=record.decided_at,
        recorded_at=record.recorded_at,
        reason=record.reason,
        evidence_ref=record.evidence_ref,
    )


class AuthoriseRunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(Launch|Resumption)$")
    reason: str = Field(min_length=1, max_length=2000)
    evidence_ref: str = Field(min_length=1, max_length=500)
    decided_at: datetime

    @field_validator("decided_at")
    @classmethod
    def _not_in_the_future(cls, value: datetime) -> datetime:
        """An authorisation cannot have been decided later than now, for the same reason
        `reports.py`'s decision endpoint refuses a future `decided_at`: the record would say
        something that has not happened yet.
        """
        if value.tzinfo is None:
            raise ValueError("decided_at must carry a timezone")
        if value > datetime.now(UTC) + _CLOCK_SKEW_ALLOWANCE:
            raise ValueError("decided_at is in the future")
        return value


@router.post(
    "/{run_id}/authorisations", response_model=RunAuthorisationOut, status_code=status.HTTP_201_CREATED
)
def authorise_run(
    run_id: str,
    body: AuthoriseRunIn,
    principal: Principal = Depends(write_access(SIP_OWNER)),
    repo: RunAuthorisationRepository = Depends(get_run_authorisation_repository),
) -> RunAuthorisationOut:
    try:
        return _out(
            repo.authorise(
                run_id,
                body.kind,
                # From the session, never the body (ADR-0004) - the record names who actually
                # authorised the run, not who the caller says did.
                actor_id=principal.user_id,
                reason=body.reason,
                evidence_ref=body.evidence_ref,
                decided_at=body.decided_at,
            )
        )
    except DecisionNotPermittedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@router.get("/{run_id}/authorisations", response_model=list[RunAuthorisationOut])
def list_run_authorisations(
    run_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: RunAuthorisationRepository = Depends(get_run_authorisation_repository),
) -> list[RunAuthorisationOut]:
    return [_out(record) for record in repo.list_for_run(run_id)]
