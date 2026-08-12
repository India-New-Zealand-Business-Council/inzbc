"""`GET /api/dashboard` (#47): everything the executive dashboard reads, in one shape.

Thin HTTP wrapper over `DashboardRepository`, the same split every other router here uses. No
aggregation logic lives in this module; it maps the repository's shape onto the wire.

**Why one endpoint rather than letting the UI compose the existing ones.** It already did: the
dashboard called `listRuns()`, took the first run, called `listCandidates(run.id)`, and tallied
verification states in TypeScript. Three problems with that, and only the third is about speed.

The UI owned a rule it should not: which run is "current", and what the full set of verification
states is. Both are facts about the domain, and both were duplicated in a language where nothing
checks them against the schema.

Open actions were unreachable. `action_register` has no endpoint, so the panel the module spec
asks for could not be built at all.

And it cost every candidate row over HTTP to produce five integers.

**Read-only, and every staff role may call it.** A dashboard the board cannot open is not an
executive dashboard, and `Board Viewer` and `Auditor` exist precisely to read without writing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from services.api.auth import STAFF_READ, Principal
from services.api.persistence import DashboardRepository, DashboardSummary
from services.api.runs import RunOut, _run_out
from services.api.session import AUTH_RESPONSES, read_access

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"], responses=AUTH_RESPONSES)


def get_dashboard_repository() -> DashboardRepository:
    """Overridden in tests, matching the other routers."""
    return DashboardRepository()


class OpenActionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_code: str
    title: str
    owner: str | None
    priority: str | None
    due_date: str | None
    status: str
    overdue: bool


class CoverageOut(BaseModel):
    """Candidate coverage for the current run.

    `by_verification` carries every state, including zeros, so the panel can render from this
    alone without knowing the enum.
    """

    model_config = ConfigDict(extra="forbid")

    total: int
    included: int
    by_verification: dict[str, int]


class DashboardOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: RunOut | None
    coverage: CoverageOut
    open_actions: list[OpenActionOut]


def _to_out(summary: DashboardSummary) -> DashboardOut:
    return DashboardOut(
        run=_run_out(summary.run) if summary.run is not None else None,
        coverage=CoverageOut(
            total=summary.total_candidates,
            included=summary.included_candidates,
            by_verification=summary.by_verification,
        ),
        open_actions=[OpenActionOut(**vars(action)) for action in summary.open_actions],
    )


@router.get("", response_model=DashboardOut)
def read_dashboard(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: DashboardRepository = Depends(get_dashboard_repository),
) -> DashboardOut:
    """Current run, candidate coverage, and open actions.

    **200 with `run: null` when no run exists**, rather than 404. "No run yet" is a state the
    dashboard renders, not an error: a 404 would make an empty system indistinguishable from a
    broken one, and the open-actions panel is still worth showing.
    """
    return _to_out(repo.summary())
