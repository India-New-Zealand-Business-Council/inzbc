"""`/api/runs/{run_id}/agent-rehearsals`: run the SIP coordinator agent from the app (Studio 6).

A **rehearsal** runs the coordinator agent (`apps/sip/core/agent_loop.py`) over a run whose launch
authority a person has already recorded, and keeps the sealed trail of what it proposed. It is
advisory, and three things about it are fixed:

- **The persisted run is not changed.** The agent works on an in-memory copy rebuilt from the
  run's own launch transition. Its mechanical transitions, the source outcomes it records and the
  brief it drafts stay in the rehearsal. The run's real source checks are recorded by an analyst
  (#344, option A) and its real transitions by `RunRepository`, as before. That keeps the
  rehearsal inside what is already approved while #55 and #189 hold production back.
- **It still stops at the QA gate.** `run_until_human_gate` halts at QA In Progress, and the agent
  cannot construct a `HumanDecision`. A model refusal, a gate refusal or the step limit ends the
  rehearsal as `stopped`, with the reason, and the partial trail is kept: a refusal is evidence too.
- **The trail can be checked again later.** It is stored as JSON with its SHA-256 chain head and,
  when `SIP_DECISION_SIGNING_KEY` is set, the HMAC seal over the head. Reading a rehearsal
  recomputes the head, checks the seal, and replays the trail through `replay_agent_audit` with no
  model call. The table is append-only.

Starting one needs Analyst or SIP Owner: the same roles that run the pipeline. Reading needs any
staff role, like the run's audit trail.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from apps.sip.collector.source_lookup import SourceIdLookup, build_source_lookups
from apps.sip.core.agent_loop import (
    AgentOrchestrator,
    AgentRunAuditLog,
    replay_agent_audit,
)
from apps.sip.core.agent_record import (
    AuditRecordFormatError,
    audit_from_json,
    audit_to_json,
)
from apps.sip.core.audit_seal import (
    SigningKeyError,
    audit_chain_head,
    seal_audit,
    seal_valid,
    signing_key_from_env,
)
from apps.sip.core.orchestrator import CorruptHistory, Orchestrator
from apps.sip.pipeline.models import RunState
from services.api.audit import record_audit
from services.api.auth import ANALYST, SIP_OWNER, STAFF_READ, Principal
from services.api.candidate_persistence import CandidateRecord, CandidateRepository
from services.api.candidates import get_candidate_repository
from services.api.model_gateway import GatewayNotConfiguredError, ModelGateway
from services.api.persistence import AuditRepository, RunRepository
from services.api.redaction import RedactionNotConfiguredError
from services.api.runs import get_audit_repository, get_run_repository
from services.api.session import AUTH_RESPONSES, read_access, write_access
from services.api.source_library import (
    SourceLibraryRepository,
    get_source_library_repository,
)

router = APIRouter(prefix="/api/runs", tags=["Agent rehearsals"], responses=AUTH_RESPONSES)

AGENT_ACTOR = "sip-agent"
DEFAULT_MAX_STEPS = 32
_SELECT = (
    "id, run_id, started_by, started_at, outcome, stop_reason, final_state, steps, audit, "
    "chain_head, seal"
)


@dataclass(frozen=True)
class RehearsalRecord:
    id: str
    run_id: str
    started_by: str
    started_at: datetime
    outcome: str
    stop_reason: str | None
    final_state: str
    steps: int
    audit: dict
    chain_head: str
    seal: str | None


def _row(row: Mapping[str, object]) -> RehearsalRecord:
    audit = row["audit"]
    return RehearsalRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        started_by=str(row["started_by"]),
        started_at=row["started_at"],  # type: ignore[arg-type]
        outcome=str(row["outcome"]),
        stop_reason=row["stop_reason"],  # type: ignore[arg-type]
        final_state=str(row["final_state"]),
        steps=int(row["steps"]),  # type: ignore[arg-type]
        audit=audit if isinstance(audit, dict) else json.loads(audit),  # type: ignore[arg-type]
        chain_head=str(row["chain_head"]),
        seal=row["seal"],  # type: ignore[arg-type]
    )


class AgentRehearsalRepository:
    """Postgres-backed store for `agent_rehearsals` (migration 0007). Insert and read only."""

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def record(
        self, *, run_id: str, started_by: str, outcome: str, stop_reason: str | None,
        final_state: str, steps: int, audit: dict, chain_head: str, seal: str | None,
    ) -> RehearsalRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into agent_rehearsals (run_id, started_by, outcome, stop_reason, "
                "final_state, steps, audit, chain_head, seal) "
                f"values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning {_SELECT}",
                (run_id, started_by, outcome, stop_reason, final_state, steps, Jsonb(audit),
                 chain_head, seal),
            ).fetchone()
            # In the same transaction, so a rehearsal never exists without the audit row saying
            # who started it.
            record_audit(
                conn, user_id=started_by, action="agent.rehearsal", record_type="runs",
                record_id=run_id, new_value=outcome, reason=stop_reason,
                approval_ref=str(row["id"]),
            )
            conn.commit()
        return _row(row)

    def for_run(self, run_id: str) -> list[RehearsalRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_SELECT} from agent_rehearsals where run_id = %s "
                "order by started_at desc, id desc limit 50",
                (run_id,),
            ).fetchall()
        return [_row(r) for r in rows]

    def get(self, run_id: str, rehearsal_id: str) -> RehearsalRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_SELECT} from agent_rehearsals where run_id = %s and id::text = %s",
                (run_id, rehearsal_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"no rehearsal {rehearsal_id!r} on run {run_id!r}")
        return _row(row)


def get_rehearsal_repository() -> AgentRehearsalRepository:
    """FastAPI dependency, overridden in tests, like `runs.get_run_repository`."""
    return AgentRehearsalRepository()


def get_agent_gateway() -> ModelGateway:
    """The live model gateway. A misconfigured provider is a 503, not a 500: nothing ran."""
    try:
        return ModelGateway()
    except GatewayNotConfiguredError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


def source_id_lookup(library: SourceLibraryRepository) -> SourceIdLookup:
    rows = [{"id": s.id, "sip185_code": s.sip185_code, "name": s.name}
            for s in library.list_sources()]
    return build_source_lookups(rows)[1]


def _collector_from(candidates: Iterable[CandidateRecord]) -> Callable[[object], list[dict]]:
    """The run's captured candidates, as the agent's collector sees them.

    Verification is passed through as the `VerificationState` a person recorded on the candidate,
    which the agent honours. The agent never sets it, and a string would be ignored.
    """
    items = [
        {"id": c.id, "headline": c.headline, "source_id": c.source_id, "url": c.url,
         "summary": c.summary, "published_at": c.published_at, "verification": c.verification}
        for c in candidates
    ]
    return lambda _window: list(items)


def launch_copy(orchestrator: Orchestrator, run_id: str) -> Orchestrator:
    """An in-memory run at Run Authorised, carrying the run's own recorded launch decision."""
    history = orchestrator.history
    if not history or history[0].to_state is not RunState.RUN_AUTHORISED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="this run has no recorded launch authority; a SIP Owner must start it first",
        )
    return Orchestrator.from_history(history[:1], run_id=run_id)


def rehearse(
    *, run_id: str, launch: Orchestrator, gateway: ModelGateway, lookup: SourceIdLookup,
    candidates: Iterable[CandidateRecord], coverage_window: tuple[str, str] | None,
    max_steps: int,
) -> tuple[AgentOrchestrator, str, str | None]:
    """Runs the agent to the QA gate or to its first refusal. Returns (agent, outcome, reason)."""
    agent = AgentOrchestrator(
        launch, run_id=run_id, gateway=gateway, source_id_lookup=lookup,
        collector_fetch=_collector_from(candidates), actor=AGENT_ACTOR,
        initial_coverage_window=coverage_window,
    )
    try:
        agent.run_until_human_gate(max_steps=max_steps)
    except (GatewayNotConfiguredError, RedactionNotConfiguredError) as error:
        if not agent.tool_records:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        return agent, "stopped", f"{type(error).__name__}: {error}"
    except Exception as error:  # noqa: BLE001 - every refusal ends the rehearsal and is recorded
        return agent, "stopped", f"{type(error).__name__}: {error}"
    return agent, "reached_qa", None


# --- HTTP -------------------------------------------------------------------------------------


class RehearsalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1, le=64)


class ToolStepOut(BaseModel):
    sequence: int
    tool: str
    reason: str
    outcome: str
    detail: str
    state_before: str
    state_after: str
    at: str


class VerificationOut(BaseModel):
    chain_intact: bool
    seal: str  # "valid", "invalid", "unsealed" or "key-not-configured"
    replay: str  # "exact", or why replay refused the trail


class RehearsalOut(BaseModel):
    id: str
    run_id: str
    started_by: str
    started_at: str
    outcome: str
    stop_reason: str | None
    final_state: str
    steps: int
    accepted: int
    refused: int
    candidates: int
    brief_summary: str | None
    production_enabled: bool
    chain_head: str
    sealed: bool
    tool_steps: list[ToolStepOut]
    verification: VerificationOut


def verify(record: RehearsalRecord, lookup: SourceIdLookup) -> VerificationOut:
    try:
        audit = audit_from_json(record.audit)
    except AuditRecordFormatError as error:
        return VerificationOut(chain_intact=False, seal="invalid", replay=f"unreadable: {error}")
    chain_intact = audit_chain_head(audit) == record.chain_head
    try:
        key = signing_key_from_env()
    except SigningKeyError:
        key = None
    if record.seal is None:
        seal = "unsealed"
    elif key is None:
        seal = "key-not-configured"
    else:
        seal = "valid" if seal_valid(audit, record.seal, key) else "invalid"
    try:
        if key is not None and record.seal is not None:
            replayed = replay_agent_audit(audit, source_id_lookup=lookup, signing_key=key,
                                          seal=record.seal)
        else:
            replayed = replay_agent_audit(audit, source_id_lookup=lookup)
        replay = ("exact" if replayed.state.value == record.final_state
                  else f"replayed to {replayed.state.value}, recorded {record.final_state}")
    except (CorruptHistory, ValueError, TypeError, KeyError) as error:
        replay = f"refused: {error}"
    return VerificationOut(chain_intact=chain_intact, seal=seal, replay=replay)


def _out(record: RehearsalRecord, lookup: SourceIdLookup) -> RehearsalOut:
    data = record.audit
    tools = data.get("tool_records", [])
    brief = data.get("brief_draft")
    return RehearsalOut(
        id=record.id,
        run_id=record.run_id,
        started_by=record.started_by,
        started_at=record.started_at.isoformat(),
        outcome=record.outcome,
        stop_reason=record.stop_reason,
        final_state=record.final_state,
        steps=record.steps,
        accepted=sum(1 for t in tools if t.get("outcome") == "accepted"),
        refused=sum(1 for t in tools if t.get("outcome") == "refused"),
        candidates=len(data.get("candidates", [])),
        brief_summary=brief.get("summary") if isinstance(brief, dict) else None,
        production_enabled=bool(data.get("production_enabled")),
        chain_head=record.chain_head,
        sealed=record.seal is not None,
        tool_steps=[
            ToolStepOut(sequence=t["sequence"], tool=t["tool"], reason=t["reason"],
                        outcome=t["outcome"], detail=t["detail"],
                        state_before=t["state_before"], state_after=t["state_after"], at=t["at"])
            for t in tools
        ],
        verification=verify(record, lookup),
    )


def _store(
    repo: AgentRehearsalRepository, *, run_id: str, principal: Principal,
    audit: AgentRunAuditLog, outcome: str, stop_reason: str | None,
) -> RehearsalRecord:
    try:
        key = signing_key_from_env()
    except SigningKeyError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return repo.record(
        run_id=run_id, started_by=principal.user_id, outcome=outcome, stop_reason=stop_reason,
        final_state=audit.transitions[-1].to_state.value if audit.transitions else "Draft",
        steps=len(audit.tool_records), audit=audit_to_json(audit),
        chain_head=audit_chain_head(audit),
        seal=seal_audit(audit, key) if key is not None else None,
    )


@router.post(
    "/{run_id}/agent-rehearsals", response_model=RehearsalOut,
    status_code=status.HTTP_201_CREATED,
)
def start_rehearsal(
    run_id: str,
    body: RehearsalIn | None = None,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    runs: RunRepository = Depends(get_run_repository),
    audits: AuditRepository = Depends(get_audit_repository),
    candidates: CandidateRepository = Depends(get_candidate_repository),
    library: SourceLibraryRepository = Depends(get_source_library_repository),
    repo: AgentRehearsalRepository = Depends(get_rehearsal_repository),
    gateway: ModelGateway = Depends(get_agent_gateway),
) -> RehearsalOut:
    """Runs the agent over an in-memory copy of a launch-authorised run, and stores the trail."""
    try:
        run = runs.get_run(run_id)
        persisted = audits.rehydrate(run_id)
    except KeyError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no run {run_id!r}") from error
    except CorruptHistory as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    launch = launch_copy(persisted, run_id)
    lookup = source_id_lookup(library)
    agent, outcome, stop_reason = rehearse(
        run_id=run_id, launch=launch, gateway=gateway, lookup=lookup,
        candidates=candidates.list_for_run(run_id),
        coverage_window=_window(run.coverage_start_utc, run.coverage_end_utc),
        max_steps=(body or RehearsalIn()).max_steps,
    )
    record = _store(repo, run_id=run_id, principal=principal, audit=agent.audit_log(),
                    outcome=outcome, stop_reason=stop_reason)
    return _out(record, lookup)


def _window(start: str, end: str) -> tuple[str, str] | None:
    """The run's own coverage window, shown to the agent, or None if it is not exactly 24h.

    The agent still has to lock it through its own tool, which checks it again.
    """
    try:
        if datetime.fromisoformat(end) - datetime.fromisoformat(start) == timedelta(hours=24):
            return (start, end)
    except (TypeError, ValueError):
        pass
    return None


@router.get("/{run_id}/agent-rehearsals", response_model=list[RehearsalOut])
def list_rehearsals(
    run_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    library: SourceLibraryRepository = Depends(get_source_library_repository),
    repo: AgentRehearsalRepository = Depends(get_rehearsal_repository),
) -> list[RehearsalOut]:
    lookup = source_id_lookup(library)
    return [_out(r, lookup) for r in repo.for_run(run_id)]


@router.get("/{run_id}/agent-rehearsals/{rehearsal_id}", response_model=RehearsalOut)
def read_rehearsal(
    run_id: str,
    rehearsal_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    library: SourceLibraryRepository = Depends(get_source_library_repository),
    repo: AgentRehearsalRepository = Depends(get_rehearsal_repository),
) -> RehearsalOut:
    try:
        record = repo.get(run_id, rehearsal_id)
    except KeyError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _out(record, source_id_lookup(library))
