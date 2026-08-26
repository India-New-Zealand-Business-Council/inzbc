"""Replaces the four-candidate demo seed with a realistic dataset for the local stack (#338).

Nothing previously seeded the SIP tables at all — `scripts/seed_demo.py`, `bench_indexes.py` and
`demo.cmd`, referenced by #338, do not exist in this repository's history. This is the seed step,
written from scratch against the schema and application code as they exist today.

**One command, against a fresh `database/schema.sql`:**

    psql "$DATABASE_URL" -f database/schema.sql   # once, on an empty database
    python -m scripts.seed_source_library          # source_library from the SIP-185 register
    python -m scripts.seed_demo

**Rerunning is safe, not additive.** Every run, action, watch, exception, comms draft and fact is
keyed on a fixed, human-readable code (`RUN-SEED-01`, `ACT-SEED-01`, ...). Before creating anything
under a code, this script checks whether it already exists and skips the whole unit if so, rather
than deleting and recreating it. That is not a shortcut: `report_versions`, `decision_records`,
`run_authorisations`, `sod_exceptions` and `candidate_sod_exceptions` all carry an
`append-only`/`no-wipe` trigger (`database/schema.sql`) that refuses `UPDATE`/`DELETE` outright, so
a delete-and-recreate strategy cannot work here even in principle — a real production database
would refuse it too. `audit_log` rows from a prior run are append-only in the same way and are
never removed; running this script twice leaves two runs' worth of `run.create` audit rows for
runs it created only once, which is the honest trail of "this script ran twice" rather than
something to hide.

**Why ten runs, not four and not two hundred.** `apps/sip/collector/tests/` already proves the
pipeline logic; this dataset exists to make the five UIs (SIP, dashboard, comms, member, FTA)
look like a system with a real operating history rather than a fixture. Ten runs, spread across
nine of the seventeen `run_state` values (Draft through Distributed and Stopped), is enough to
give the runs list a real spread of state badges and the candidate list in the busiest run enough
rows (~18) to scroll, without requiring hours of hand-curated synthetic headlines per run the way
`bench_indexes.py`'s 200-run/50k-candidate scale would.

**What is real and what is synthetic.** Every `source_id` a candidate carries resolves to a real
row in `source_library`, seeded from the actual approved SIP-185 v1.0 register
(`apps/sip/collector/source_register.py`) — no invented publications. Every headline, summary and
comms/facts text body in this file is synthetic and is prefixed `[SEED]` for exactly that reason:
none of it is a real news item, a real trade figure, a real member name or a real quote, and none
of it should be read as one (`PROJECT-RULES.md`). Users are fictional placements under
`@seed.inzbc.test`, not real staff.

**What this dataset does not prove.** It is representative, not real operating history: no real
SIP-184 run has ever executed against this schema (`#55` is still open), so nothing here reflects
an actual day's collection. The decision-kind choices behind each human gate (which
`decision_records` row authorises which state transition) are this script's own reading of
`apps/sip/core/orchestrator.py`'s gate table applied to `apps/sip/pipeline/models.py`'s three
decision kinds — `services/api/persistence.py.apply_transition` only checks that the referenced
`decision_records` row exists, not that its `kind` matches the gate's purpose, so this is a
plausible narrative fit, not a verified one. Full rationale in `docs/seed-demo-dataset.md`.
"""

from __future__ import annotations

import hashlib
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from apps.sip.collector.dedupe import find_duplicate_of
from apps.sip.collector.source_register import (
    ALL_SOURCES,
    MANDATORY_SOURCES,
)
from apps.sip.collector.verification import enforce_verification_gate
from apps.sip.pipeline.models import (
    RunState,
    SignalStrength,
    SourceConfidence,
    VerificationState,
)
from scripts.seed_source_library import main as seed_source_library
from services.api.candidate_persistence import CandidateRepository
from services.api.decisions import (
    CEO_RULING,
    DISTRIBUTION_AUTHORITY,
    REPORT_APPROVAL,
    DecisionRepository,
    ReportRepository,
)
from services.api.persistence import RunRepository
from services.api.source_checks import SourceCheckRepository
from services.api.tests.role_seed import authorise_run, grant, role_id

_TAG = "[SEED]"
_EMAIL_DOMAIN = "seed.inzbc.test"
_ANCHOR = date(
    2026, 7, 6
)  # a fixed Monday; deterministic so reruns compute the same dates


def _database_url() -> str:
    return os.environ["DATABASE_URL"]


def _connect() -> psycopg.Connection:
    return psycopg.connect(_database_url(), row_factory=dict_row)


# ---------------------------------------------------------------------------
# 1. Roles and users
# ---------------------------------------------------------------------------

ROLE_NAMES = (
    "SIP Owner",
    "Analyst",
    "Reviewer",
    "Secretariat",
    "Administrator",
    "Board Viewer",
    "Auditor",
)


@dataclass(frozen=True)
class SeedUser:
    key: str
    name: str
    roles: tuple[str, ...]


SEED_USERS = (
    SeedUser("owner", "Grace Liu", ("SIP Owner", "Administrator")),
    SeedUser("analyst", "Priya Nair", ("Analyst", "Secretariat")),
    SeedUser("reviewer", "Daniel Osei", ("Reviewer", "Analyst")),
    SeedUser("reviewer2", "Aroha Campbell", ("Reviewer", "Secretariat")),
    SeedUser("board", "Wiremu Rangi", ("Board Viewer",)),
    SeedUser("auditor", "Sam Patel", ("Auditor",)),
)


def _seed_users(conn: psycopg.Connection) -> dict[str, str]:
    """Creates (or reuses) the seed users, returns key -> user id.

    Keyed on email, which `users.email` declares unique, so a rerun resolves the same row rather
    than colliding — no separate existence check needed before the insert itself.

    Each row also gets a deterministic `github_login` (`seed-<key>`), so a local walkthrough can
    actually sign in as one of these people via `python -m scripts.dev_session --github-login
    seed-owner` (`services/api/auth.py`'s `establish_session`) rather than the dataset only being
    visible over a direct database read.
    """
    ids: dict[str, str] = {}
    for user in SEED_USERS:
        email = f"{user.name.lower().replace(' ', '.')}@{_EMAIL_DOMAIN}"
        github_login = f"seed-{user.key}"
        row = conn.execute(
            "insert into users (name, email, github_login) values (%s, %s, %s) "
            "on conflict (email) do update set name = excluded.name, "
            "github_login = excluded.github_login returning id",
            (user.name, email, github_login),
        ).fetchone()
        user_id = str(row["id"])
        ids[user.key] = user_id
        grant(conn, user_id, *user.roles)
    conn.commit()
    return ids


# ---------------------------------------------------------------------------
# 2. Candidate fixtures — drawn from the real source register, synthetic content
# ---------------------------------------------------------------------------

# A slice of ALL_SOURCES to draw from, picked for spread across country/layer rather than at
# random, so a rerun's source_id assignment is deterministic.
_BYLINE_SOURCES = [
    s for s in ALL_SOURCES if s.category in ("News", "Trade body", "Government")
][:24] or list(ALL_SOURCES[:24])


@dataclass
class CandidateSpec:
    headline: str
    summary: str
    url: str
    source_index: int  # index into _BYLINE_SOURCES
    signal: SignalStrength | None = None
    confidence: SourceConfidence | None = None
    verification: VerificationState | None = None
    duplicate_of_index: int | None = None  # index into the same run's spec list


_HEADLINE_TOPICS = (
    "kiwifruit exporters respond to India quota review",
    "dairy sector watches India tariff-line consultation",
    "wine exporters ask about the MFN clause carve-out",
    "manuka honey duty cut takes effect on schedule",
    "wool trade mission reports early India buyer interest",
    "forestry products face new India phytosanitary check",
    "India-NZ services chapter talks reported to resume",
    "seafood exporters flag India cold-chain certification gap",
    "red meat sector requests clarity on rules of origin",
    "education providers see India student visa policy shift",
    "horticulture group welcomes India market access briefing",
    "India investment delegation visit reported for next quarter",
    "FTA implementation committee meeting readout published",
    "India customs digitisation pilot covers NZ export lanes",
    "member survey flags India compliance-cost concerns",
    "India state-level trade office opens NZ liaison channel",
    "pharma sector queries India regulatory approval timeline",
    "technology exporters note India data-localisation proposal",
)


def _build_candidates(run_index: int, count: int) -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []
    for i in range(count):
        topic = _HEADLINE_TOPICS[(run_index * 5 + i) % len(_HEADLINE_TOPICS)]
        source_idx = (run_index * 3 + i) % len(_BYLINE_SOURCES)
        specs.append(
            CandidateSpec(
                headline=f"{_TAG} {topic.capitalize()}",
                summary=f"{_TAG} synthetic wire-style summary for a walkthrough fixture; "
                "not a real report on this topic.",
                url=f"https://example.invalid/seed/run-{run_index:02d}/item-{i:02d}",
                source_index=source_idx,
            )
        )
    return specs


def _inject_duplicates(specs: list[CandidateSpec]) -> None:
    """Appends two candidates engineered to match earlier ones in `specs` via `dedupe.py`'s real
    normalization — a case+trailing-slash url variant and a whitespace/case headline variant —
    so `find_duplicate_of` (called on every run in `_capture_and_work_candidates`) has genuine
    duplicates to catch rather than an all-distinct batch. No-op on a short/empty batch.
    """
    if len(specs) < 4:
        return
    url_source = specs[0]
    specs.append(
        CandidateSpec(
            headline=f"{url_source.headline} (wire copy)",
            summary=f"{_TAG} syndicated wire copy of an earlier item in this batch — matches by "
            "url, not headline.",
            url=url_source.url.upper() + "/",
            source_index=url_source.source_index,
        )
    )
    title_source = specs[1]
    specs.append(
        CandidateSpec(
            headline="  " + title_source.headline.upper() + "  ",
            summary=f"{_TAG} independently captured under a different url — matches an earlier "
            "item by normalized headline.",
            url=f"https://example.invalid/seed/dup/{uuid.uuid4().hex[:10]}",
            source_index=title_source.source_index,
        )
    )


def _apply_mix(specs: list[CandidateSpec]) -> None:
    """Assigns a realistic, non-uniform spread of signal/confidence/verification in place —
    #338 explicitly asks for Unverified and Rejected to appear, not an all-Verified dataset.
    """
    pattern = [
        (SignalStrength.HIGH, SourceConfidence.HIGH, VerificationState.VERIFIED),
        (
            SignalStrength.MEDIUM,
            SourceConfidence.MEDIUM,
            VerificationState.PARTIALLY_VERIFIED,
        ),
        (SignalStrength.LOW, SourceConfidence.LOW, VerificationState.UNVERIFIED),
        (SignalStrength.MEDIUM, SourceConfidence.HIGH, VerificationState.VERIFIED),
        (SignalStrength.LOW, SourceConfidence.UNVERIFIED, VerificationState.UNVERIFIED),
        (SignalStrength.CRITICAL, SourceConfidence.HIGH, VerificationState.VERIFIED),
        (None, None, VerificationState.REJECTED),
    ]
    for i, spec in enumerate(specs):
        signal, confidence, verification = pattern[i % len(pattern)]
        spec.signal, spec.confidence, spec.verification = (
            signal,
            confidence,
            verification,
        )


# ---------------------------------------------------------------------------
# 3. Runs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunSpec:
    number: str
    day_offset: int  # days after _ANCHOR
    target_state: RunState
    candidate_count: int
    full_source_coverage: (
        bool  # False => leaves mandatory sources uncovered, deliberately
    )
    analyst_key: str
    reviewer_key: str


RUN_SPECS = (
    RunSpec("RUN-SEED-01", 0, RunState.DRAFT, 0, True, "analyst", "reviewer"),
    RunSpec("RUN-SEED-02", 1, RunState.RUN_AUTHORISED, 0, True, "analyst", "reviewer"),
    RunSpec("RUN-SEED-03", 2, RunState.COVERAGE_LOCKED, 0, True, "analyst", "reviewer"),
    RunSpec("RUN-SEED-04", 3, RunState.SCANNING, 6, True, "analyst", "reviewer"),
    RunSpec(
        "RUN-SEED-05", 4, RunState.CANDIDATE_REVIEW, 18, False, "analyst", "reviewer2"
    ),
    RunSpec("RUN-SEED-06", 5, RunState.REPORT_DRAFTED, 9, True, "reviewer", "analyst"),
    RunSpec("RUN-SEED-07", 6, RunState.QA_FAILED, 8, True, "analyst", "reviewer2"),
    RunSpec("RUN-SEED-08", 7, RunState.PAUSED, 7, False, "reviewer2", "analyst"),
    RunSpec("RUN-SEED-09", 9, RunState.DISTRIBUTED, 12, True, "analyst", "reviewer"),
    RunSpec("RUN-SEED-10", 11, RunState.STOPPED, 10, True, "reviewer", "reviewer2"),
)


def _run_exists(conn: psycopg.Connection, run_number: str) -> str | None:
    row = conn.execute(
        "select id from runs where run_number = %s", (run_number,)
    ).fetchone()
    return str(row["id"]) if row else None


def _record_all_source_checks(
    run_id: str, source_lookup: dict[str, str], *, full: bool, actor_id: str
) -> None:
    """Records source_checks for this run's mandatory-source coverage.

    `full=False` deliberately stops partway through `MANDATORY_SOURCES`, leaving the rest
    uncovered — #338 asks for at least one run where `missing_mandatory_outcomes()` has
    something real to report, not an always-clean gate.
    """
    repo = SourceCheckRepository(_database_url())
    sources = (
        MANDATORY_SOURCES if full else MANDATORY_SOURCES[: len(MANDATORY_SOURCES) // 2]
    )
    for entry in sources:
        db_id = source_lookup.get(entry.source_id)
        if db_id is None:
            continue
        repo.record(
            run_id,
            db_id,
            _outcome_for(entry.source_id),
            method="Direct access",
            fallback_used=False,
            access_error=None,
            notes=f"{_TAG} measured seed run, not a real SIP-184 execution",
            actor_id=actor_id,
        )


def _outcome_for(source_id: str):
    from apps.sip.pipeline.models import SourceOutcome

    # A small, deterministic spread of non-Included outcomes so the source-check table isn't a
    # wall of identical rows.
    bucket = sum(source_id.encode()) % 11
    if bucket == 0:
        return SourceOutcome.NO_QUALIFYING_ITEM
    if bucket == 1:
        return SourceOutcome.INACCESSIBLE
    return SourceOutcome.INCLUDED


def _capture_and_work_candidates(
    conn: psycopg.Connection,
    run_id: str,
    specs: list[CandidateSpec],
    source_lookup_by_code: dict[str, str],
    *,
    captor_id: str,
    verifier_id: str,
    owner_id: str,
    score_now: bool,
    verify_now: bool,
) -> list[dict]:
    """Captures every candidate, then (if asked) verifies and scores it in the order the
    verification gate requires — score after verify, never before, so a High/Critical signal is
    never set on a still-Unverified row (`apps/sip/collector/verification.py`).
    """
    cand_repo = CandidateRepository(_database_url())
    created: list[dict] = []
    for spec in specs:
        source_entry = _BYLINE_SOURCES[spec.source_index]
        db_source_id = source_lookup_by_code.get(source_entry.source_id)
        record = cand_repo.capture(
            run_id=run_id,
            headline=spec.headline,
            source_id=db_source_id,
            url=spec.url,
            summary=spec.summary,
            published_at=None,
            in_coverage_window=True,
            actor_id=captor_id,
        )
        created.append(
            {"id": record.id, "headline": record.headline, "url": record.url}
        )

    if verify_now:
        for spec, row in zip(specs, created, strict=True):
            if spec.verification is None:
                continue
            cand_repo.record_verification(
                row["id"],
                spec.verification,
                actor_id=verifier_id,
                reason=f"{_TAG} seed verification pass",
            )

    if score_now:
        for spec, row in zip(specs, created, strict=True):
            if spec.signal is None:
                continue
            try:
                enforce_verification_gate(spec.signal, spec.verification)
            except Exception:
                continue  # a Rejected/Unverified row correctly cannot carry a High/Critical signal
            cand_repo.record_score(
                row["id"],
                signal=spec.signal,
                confidence=spec.confidence,
                nz_relevance=3,
                india_relevance=3,
                member_relevance=2,
                actor_id=captor_id if captor_id != verifier_id else owner_id,
                reason=f"{_TAG} seed scoring pass",
            )

    # Cross-run + within-run duplicate detection, via the real dedupe logic (dedupe.py), not a
    # hand-picked flag — #338 wants the dedupe logic shown doing real work, not asserted.
    seen: list[dict] = []
    for spec, row in zip(specs, created, strict=True):
        article = {"url": row["url"], "title": row["headline"]}
        duplicate_id = find_duplicate_of(article, seen)
        if duplicate_id:
            cand_repo.merge(
                row["id"],
                duplicate_id,
                actor_id=captor_id,
                reason=f"{_TAG} matched an earlier candidate in this run by dedupe.py",
            )
        seen.append({"id": row["id"], "url": row["url"], "headline": row["headline"]})

    return created


def _record_sod_exception(
    conn: psycopg.Connection, candidate_id: str, actor_id: str, approver_id: str
) -> str:
    row = conn.execute(
        "insert into candidate_sod_exceptions (candidate_id, actor_id, approved_by, reason, "
        "review_date) values (%s, %s, %s, %s, %s) "
        "on conflict (candidate_id, actor_id) do update set reason = excluded.reason "
        "returning id",
        (
            candidate_id,
            actor_id,
            approver_id,
            f"{_TAG} single-analyst placement window; steady-state staffing has one person "
            "holding every SIP role, so this exception is deliberate rather than a gap.",
            date.today() + timedelta(days=180),
        ),
    ).fetchone()
    conn.commit()
    return str(row["id"])


def _report_and_decide(
    run_id: str,
    *,
    author_id: str,
    author_role_names: tuple[str, ...],
    decider_id: str,
    decider_role_id: int,
    ceo_value: str,
    report_value: str,
    distribution_value: str,
) -> tuple[str, dict[str, str]]:
    """Submits one report version and records all three decision kinds against it.

    Returns the report version id (for `record_qa`) and the decision-record ids keyed by kind, so
    the caller can use the right one as `approval_ref` for each state-machine gate. See the module
    docstring for which kind stands in for which gate.
    """
    report_repo = ReportRepository(_database_url())
    decision_repo = DecisionRepository(_database_url())

    content = f"{_TAG} report content placeholder for {run_id}".encode()
    version = report_repo.submit(
        run_id=run_id,
        content_sha256=hashlib.sha256(content).hexdigest(),
        actor_id=author_id,
        role_names=author_role_names,
        created_at=datetime.now(UTC),
    )

    decided_at = datetime.now(UTC)
    next_review = date.today() + timedelta(days=90)
    ids: dict[str, str] = {}
    for kind, value in (
        (REPORT_APPROVAL, report_value),
        (CEO_RULING, ceo_value),
        (DISTRIBUTION_AUTHORITY, distribution_value),
    ):
        record = decision_repo.record(
            report_version_id=version.id,
            kind=kind,
            value=value,
            actor_id=decider_id,
            actor_role_id=decider_role_id,
            reason=f"{_TAG} seed decision — {kind} recorded for the walkthrough dataset",
            evidence_ref=f"{_TAG} seed evidence reference",
            owner_id=decider_id,
            next_review=next_review,
            decided_at=decided_at,
            idempotency_key=uuid.uuid4(),
            expected_head_revision=0,
            distribution_recipient=(
                "board@seed.inzbc.test" if kind == DISTRIBUTION_AUTHORITY else None
            ),
        )
        ids[kind] = record.id
    return version.id, ids


def _build_source_lookup_by_code(conn: psycopg.Connection) -> dict[str, str]:
    rows = conn.execute(
        "select sip185_code, id from source_library where sip185_code is not null"
    )
    return {row["sip185_code"]: str(row["id"]) for row in rows.fetchall()}


def _walk_run(
    run_id: str, target: RunState, *, actor_id: str, refs: dict[RunState, str | None]
) -> None:
    """Drives a run from Draft to `target`, one legal transition at a time, supplying whatever
    `approval_ref` each gate needs from `refs` (keyed by the *target* state of the gated hop).
    """
    run_repo = RunRepository(_database_url())
    path = [
        RunState.DRAFT,
        RunState.RUN_AUTHORISED,
        RunState.COVERAGE_LOCKED,
        RunState.SCANNING,
        RunState.CANDIDATE_REVIEW,
        RunState.REPORT_DRAFTED,
        RunState.QA_IN_PROGRESS,
    ]
    if target in (RunState.QA_FAILED,):
        path += [RunState.QA_FAILED]
    elif target in (
        RunState.AWAITING_CEO_DECISION,
        RunState.PAUSED,
        RunState.STOPPED,
        RunState.APPROVED_FOR_MANUAL_DISTRIBUTION,
        RunState.DISTRIBUTED,
    ):
        path += [RunState.AWAITING_CEO_DECISION]
        if target in (RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, RunState.DISTRIBUTED):
            path += [RunState.APPROVED_FOR_MANUAL_DISTRIBUTION]
            if target is RunState.DISTRIBUTED:
                path += [RunState.DISTRIBUTED]
        elif target in (RunState.PAUSED, RunState.STOPPED):
            path += [target]

    idx = path.index(target)
    steps = path[: idx + 1]

    run = run_repo.get_run(run_id)
    for state in steps[1:]:
        if run.state == state:
            continue
        run = run_repo.apply_transition(
            run_id,
            run.version,
            state,
            actor_id=actor_id,
            reason=f"{_TAG} seed walkthrough transition to {state.value}",
            approval_ref=refs.get(state),
        )


def _seed_runs(
    conn: psycopg.Connection, user_ids: dict[str, str], source_lookup: dict[str, str]
) -> None:
    run_repo = RunRepository(_database_url())
    owner_role = role_id(conn, "SIP Owner")
    for kind in (CEO_RULING, REPORT_APPROVAL, DISTRIBUTION_AUTHORITY):
        conn.execute(
            "insert into decision_role_permissions (kind, actor_role_id) values (%s, %s) "
            "on conflict (kind, actor_role_id) do update set enabled = true",
            (kind, owner_role),
        )
    conn.commit()

    for run_index, spec in enumerate(RUN_SPECS):
        existing = _run_exists(conn, spec.number)
        if existing is not None:
            print(f"  {spec.number}: already seeded, skipping")
            continue

        coverage_start = datetime.combine(
            _ANCHOR + timedelta(days=spec.day_offset), datetime.min.time(), tzinfo=UTC
        )
        coverage_end = coverage_start + timedelta(hours=20)
        run = run_repo.create_run(
            spec.number,
            "SIP-050 v1.1",
            coverage_start.isoformat(),
            coverage_end.isoformat(),
            initiated_by=user_ids["owner"],
        )
        conn.execute(
            "update runs set analyst_id = %s, reviewer_id = %s where id = %s",
            (user_ids[spec.analyst_key], user_ids[spec.reviewer_key], run.id),
        )
        conn.commit()

        refs: dict[RunState, str | None] = {}
        if spec.target_state != RunState.DRAFT:
            launch_ref = authorise_run(conn, run.id, user_ids["owner"], kind="Launch")
            refs[RunState.RUN_AUTHORISED] = launch_ref

        specs: list[CandidateSpec] = []
        if spec.candidate_count:
            specs = _build_candidates(run_index, spec.candidate_count)
            _inject_duplicates(specs)
            _apply_mix(specs)
            reached_scanning = (
                spec.target_state != RunState.RUN_AUTHORISED
                and spec.target_state != RunState.COVERAGE_LOCKED
            )
            if reached_scanning:
                created = _capture_and_work_candidates(
                    conn,
                    run.id,
                    specs,
                    source_lookup,
                    captor_id=user_ids[spec.analyst_key],
                    verifier_id=user_ids[spec.reviewer_key],
                    owner_id=user_ids["owner"],
                    score_now=spec.target_state not in (RunState.SCANNING,),
                    verify_now=spec.target_state not in (RunState.SCANNING,),
                )
                if spec.number == "RUN-SEED-05" and created:
                    # One deliberate self-verification exception: the analyst both captured and
                    # verified this one candidate, authorised by the SIP Owner. Demonstrates the
                    # exception path survives rather than asserting it in prose.
                    target_candidate = created[0]["id"]
                    exception_id = _record_sod_exception(
                        conn,
                        target_candidate,
                        user_ids[spec.analyst_key],
                        user_ids["owner"],
                    )
                    CandidateRepository(_database_url()).record_verification(
                        target_candidate,
                        VerificationState.VERIFIED,
                        actor_id=user_ids[spec.analyst_key],
                        reason=f"{_TAG} self-verification under a recorded SoD exception",
                        sod_exception_id=exception_id,
                    )

        if spec.target_state in (
            RunState.SCANNING,
            RunState.CANDIDATE_REVIEW,
            RunState.REPORT_DRAFTED,
            RunState.QA_FAILED,
            RunState.PAUSED,
            RunState.DISTRIBUTED,
            RunState.STOPPED,
        ):
            _record_all_source_checks(
                run.id,
                source_lookup,
                full=spec.full_source_coverage,
                actor_id=user_ids["owner"],
            )

        if spec.target_state == RunState.REPORT_DRAFTED:
            # A report exists but is not yet decided — the "submitted, undecided" state #338 asks
            # the freshness/decision UI to be able to show, distinct from "no report at all".
            report_repo = ReportRepository(_database_url())
            content = f"{_TAG} report content placeholder for {run.id}".encode()
            report_repo.submit(
                run_id=run.id,
                content_sha256=hashlib.sha256(content).hexdigest(),
                actor_id=user_ids[spec.reviewer_key],
                role_names=("Reviewer", "Analyst", "SIP Owner"),
                created_at=datetime.now(UTC),
            )

        elif spec.target_state in (
            RunState.QA_FAILED,
            RunState.DISTRIBUTED,
            RunState.STOPPED,
            RunState.PAUSED,
        ):
            # Every one of these states sits past Awaiting CEO Decision (or, for QA Failed, past
            # the QA gate) per apps/sip/core/orchestrator.py's `_LEGAL` table, and every gate past
            # Report Drafted needs a `decision_records` row to point `approval_ref` at — there is
            # no other kind of evidence the persistence layer accepts. `decisions.py`'s `record`
            # only requires the referenced report version to exist and the decider to differ from
            # its author; it does not require the run to already be sitting in a matching state,
            # so recording all three decisions right after submission and walking the run through
            # its gates afterwards is a legal, if narratively compressed, sequence.
            report_value = (
                "Rejected" if spec.target_state == RunState.QA_FAILED else "Approved"
            )
            ceo_value = {
                RunState.STOPPED: "Stop",
                RunState.PAUSED: "Pause",
                RunState.DISTRIBUTED: "Continue",
                RunState.QA_FAILED: "Continue With Correction",
            }[spec.target_state]
            distribution_value = (
                "Authorised"
                if spec.target_state == RunState.DISTRIBUTED
                else "Not Authorised"
            )
            version_id, decision_ids = _report_and_decide(
                run.id,
                author_id=user_ids[spec.reviewer_key],
                author_role_names=("Reviewer", "Analyst", "SIP Owner"),
                decider_id=user_ids["owner"],
                decider_role_id=owner_role,
                ceo_value=ceo_value,
                report_value=report_value,
                distribution_value=distribution_value,
            )
            refs[RunState.QA_FAILED] = decision_ids.get(REPORT_APPROVAL)
            refs[RunState.AWAITING_CEO_DECISION] = decision_ids.get(REPORT_APPROVAL)
            refs[RunState.APPROVED_FOR_MANUAL_DISTRIBUTION] = decision_ids.get(
                DISTRIBUTION_AUTHORITY
            )
            refs[RunState.DISTRIBUTED] = decision_ids.get(DISTRIBUTION_AUTHORITY)
            refs[RunState.STOPPED] = decision_ids.get(CEO_RULING)
            refs[RunState.PAUSED] = decision_ids.get(CEO_RULING)

            qa_result = "Fail" if spec.target_state == RunState.QA_FAILED else "Pass"
            ReportRepository(_database_url()).record_qa(
                version_id,
                result=qa_result,
                critical_failures=1 if qa_result == "Fail" else 0,
                actor_id=user_ids["owner"],
                notes=f"{_TAG} seed SIP-188 QA {qa_result.lower()}",
            )

        _walk_run(run.id, spec.target_state, actor_id=user_ids["owner"], refs=refs)
        print(f"  {spec.number}: seeded to {spec.target_state.value}")


# ---------------------------------------------------------------------------
# 4. Lightweight secondary registers (dashboard / comms UI), so no screen is empty
# ---------------------------------------------------------------------------


def _seed_secondary_registers(
    conn: psycopg.Connection, user_ids: dict[str, str]
) -> None:
    from services.api.comms_persistence import CommsDraftRepository
    from services.api.facts_persistence import FactRepository
    from services.api.registers_persistence import (
        ActionRegisterRepository,
        ExceptionRepository,
        WatchListRepository,
    )

    actions = ActionRegisterRepository(_database_url())
    for code, title, status in (
        (
            "ACT-SEED-01",
            f"{_TAG} confirm India tariff-line figure with a manual source check",
            "Open",
        ),
        (
            "ACT-SEED-02",
            f"{_TAG} review uncovered mandatory sources on RUN-SEED-05",
            "Open",
        ),
        (
            "ACT-SEED-03",
            f"{_TAG} close out QA correction from RUN-SEED-07",
            "Controlled Monitoring",
        ),
    ):
        if conn.execute(
            "select 1 from action_register where action_code = %s", (code,)
        ).fetchone():
            continue
        actions.create(
            code,
            title,
            status,
            actor_id=user_ids["owner"],
            owner_id=user_ids["analyst"],
            priority="Medium",
        )

    watches = WatchListRepository(_database_url())
    for code, title in (
        ("WL-SEED-01", f"{_TAG} India Ministry of Commerce tariff-line notices"),
        ("WL-SEED-02", f"{_TAG} India customs digitisation rollout"),
    ):
        if conn.execute(
            "select 1 from watch_lists where watch_code = %s", (code,)
        ).fetchone():
            continue
        watches.create(
            code, title, "Active", actor_id=user_ids["owner"], frequency="Weekly"
        )

    exceptions = ExceptionRepository(_database_url())
    if not conn.execute(
        "select 1 from exceptions where exception_type = %s", (f"{_TAG} coverage gap",)
    ).fetchone():
        exceptions.record(
            f"{_TAG} coverage gap",
            "Medium",
            "Open",
            actor_id=user_ids["owner"],
            owner_id=user_ids["analyst"],
        )

    drafts = CommsDraftRepository(_database_url())
    existing_drafts = conn.execute(
        "select count(*) as n from comms_drafts where brief like %s", (f"{_TAG}%",)
    ).fetchone()["n"]
    if existing_drafts == 0:
        drafts.create(
            "newsletter",
            f"{_TAG} monthly member newsletter draft",
            f"{_TAG} synthetic newsletter body for the local demo stack.",
            authored_by=user_ids["reviewer"],
        )

    facts = FactRepository(_database_url())
    if not conn.execute(
        "select 1 from approved_facts where fact_key = %s", ("SEED-FACT-001",)
    ).fetchone():
        drafted = facts.draft(
            "SEED-FACT-001",
            f"{_TAG} placeholder approved fact for the demo stack.",
            f"{_TAG} synthetic source, not a real citation",
            actor_id=user_ids["analyst"],
            owner_id=user_ids["analyst"],
        )
        facts.approve(drafted.id, actor_id=user_ids["owner"])

    conn.commit()


def main() -> int:
    print("seeding source_library from the SIP-185 register...")
    seed_source_library()

    with _connect() as conn:
        print("seeding roles and users...")
        user_ids = _seed_users(conn)

        source_lookup = _build_source_lookup_by_code(conn)

        print("seeding runs, candidates, source checks, reports and decisions...")
        _seed_runs(conn, user_ids, source_lookup)

        print(
            "seeding action register, watch lists, exceptions, comms drafts, facts..."
        )
        _seed_secondary_registers(conn, user_ids)

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
