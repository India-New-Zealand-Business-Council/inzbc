"""Walk one run the whole length of the SIP-184 state machine, Draft -> Distributed -> Closed (#55).

**Not a SIP-184 production run.** Same standing as `run_dry_run.py`: SIP-191's launch window
(`docs/sip/launch/launch-config.md`) expired on 31 Jul 2026 with no re-approval on record, and
SIP-184 step 1 treats an out-of-window run as a Critical stop. `run_number` is stamped
`WALK-...`, `production_enabled` stays false and nothing is deployed. This script exists to prove
that a run *can* be taken across every human gate by the account meant to cross it, and to read
`decision_records` and `audit_log` back afterwards - the evidence #55 asks for - not to produce a
Production Run Register entry.

**Why hybrid HTTP + in-process.** The lifecycle HTTP surface is incomplete: `services/api/runs.py`
mounts `create`, `/start` (Draft -> Run Authorised), `pause`, `resume`, `fail-qa`, `stop` and
`/complete` (Distributed -> Closed), but nothing for the mechanical advances in between
(`Run Authorised -> Coverage Locked -> Scanning -> Candidate Review -> Report Drafted ->
QA In Progress`) or for `Awaiting CEO Decision -> Approved for Manual Distribution ->
Distributed`. Those transitions are not human gates - the orchestrator drives them itself
(`apps/sip/core/orchestrator.py._HUMAN_GATED` does not list them) - so this script drives them
directly through `RunRepository.apply_transition`, the same call the (unbuilt) endpoints would
make. **Every human gate is still crossed over HTTP, by a distinct role account:**

    Draft -> Run Authorised                     POST /api/runs/{id}/authorisations + /start   SIP Owner
    QA In Progress -> Awaiting CEO Decision      apply_transition, approval_ref = CEO Ruling record
    Awaiting CEO Decision -> Approved for ...    apply_transition, approval_ref = Distribution record
    Approved for ... -> Distributed              apply_transition, approval_ref = Distribution record

The three decision records those gates point at are recorded over HTTP through
`POST /api/reports/{id}/ruling|approval|distribution` by the SIP Owner, Reviewer and Secretariat
respectively; the report version is submitted over HTTP by the Analyst. Separation of duties
(`services/api/decisions.py`) holds because the Analyst who authors the report never decides on
it.

**Accounts.** Seeds four users under `@walk.inzbc.test`, one role each (Analyst, Reviewer,
SIP Owner, Secretariat), grants the roles and mints a session per account in-process - the same
steps `.github/workflows/sip-dry-run.yml` does in shell for its single Analyst. Needs
`DATABASE_URL` directly for that, exactly as `scripts/dev_session.py` does and for the same
reason: there is no sign-in route to call over HTTP.

**Prerequisites** (see `scripts/seed_demo.py`'s header for the canonical sequence):

    createdb inzbc_walk
    psql "$DATABASE_URL" -f database/schema.sql
    psql "$DATABASE_URL" -f database/migrations/0003_seed_roles_and_decision_permissions.sql
    python -m scripts.seed_source_library
    uvicorn services.api.main:app --port 8000      # in another shell
    DATABASE_URL=... python -m apps.sip.collector.walk_full_run \
        --base-url http://127.0.0.1:8000 --evidence-out walk_evidence.json

Migration 0003 is required here (unlike CI's schema-only gate): without
`decision_role_permissions` rows every decision kind is refused, so no gate past QA can be
crossed. #360 tracks two unrelated pre-existing tests that 0003 breaks locally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import requests

from apps.sip.pipeline.models import RunState
from services.api.auth import SessionRepository
from services.api.persistence import RunRepository
from services.api.tests.role_seed import grant

_AUCKLAND = ZoneInfo("Pacific/Auckland")

# One user per role. Kept deliberately small: the walk needs exactly the accounts that cross a
# gate, plus the Analyst who authors the report the gates decide on.
_ACCOUNTS: dict[str, str] = {
    "walk-analyst": "Analyst",
    "walk-reviewer": "Reviewer",
    "walk-sip-owner": "SIP Owner",
    "walk-secretariat": "Secretariat",
}


@dataclass
class Account:
    github_login: str
    role: str
    user_id: str
    cookie: str
    csrf: str

    def session(self, base_url: str) -> requests.Session:
        s = requests.Session()
        s.cookies.set("inzbc_session", self.cookie)
        s.headers.update({"X-CSRF-Token": self.csrf})
        s.base_url = base_url  # type: ignore[attr-defined]
        return s


def _locked_coverage_window(now_utc: datetime) -> tuple[str, str]:
    """SIP-184 step 2: previous day 07:00 to current day 07:00 Pacific/Auckland, exact 24h."""
    now_nz = now_utc.astimezone(_AUCKLAND)
    end_nz = now_nz.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_nz.hour < 7:
        end_nz -= timedelta(days=1)
    start_nz = end_nz - timedelta(days=1)
    return start_nz.astimezone(UTC).isoformat(), end_nz.astimezone(UTC).isoformat()


def _seed_accounts(database_url: str) -> dict[str, Account]:
    """Create the four role users, grant the roles, mint a session for each. In-process because
    there is no HTTP path to any of it (`scripts/dev_session.py`'s docstring).
    """
    sessions = SessionRepository(database_url)
    accounts: dict[str, Account] = {}
    with psycopg.connect(database_url) as conn:
        for login, role in _ACCOUNTS.items():
            row = conn.execute(
                "insert into users (id, name, email, github_login) "
                "values (gen_random_uuid(), %s, %s, %s) "
                "on conflict (github_login) do update set name = excluded.name "
                "returning id",
                (f"Walk {role}", f"{login}@walk.inzbc.test", login),
            ).fetchone()
            user_id = str(row[0])
            with conn.transaction():
                grant(conn, user_id, role)
            accounts[role] = Account(login, role, user_id, cookie="", csrf="")
        conn.commit()
    for role, account in accounts.items():
        principal = sessions.establish_session(account.github_login)
        account.cookie = principal.session_id
        account.csrf = principal.csrf_token
        assert role in principal.roles, (
            f"{account.github_login} did not get {role}: {principal.roles}"
        )
    return accounts


def _post(session: requests.Session, path: str, body: dict | None = None) -> dict:
    response = session.request(
        "POST",
        f"{session.base_url}{path}",
        json=body,
        timeout=30,  # type: ignore[attr-defined]
    )
    if not response.ok:
        raise SystemExit(f"POST {path} -> {response.status_code}: {response.text}")
    return response.json() if response.content else {}


def _decision_body(
    actor_id: str, value: str, head_revision: int, **extra: object
) -> dict:
    now = datetime.now(UTC)
    return {
        "value": value,
        "reason": f"walk-through of the {value!r} gate for #55 evidence",
        "evidence_ref": "SIP-184 walk-through run record",
        "owner_id": actor_id,
        "next_review": (now + timedelta(days=30)).date().isoformat(),
        "decided_at": now.isoformat(),
        "idempotency_key": str(uuid.uuid4()),
        "expected_head_revision": head_revision,
        **extra,
    }


def run_walk(base_url: str, database_url: str) -> dict:
    accounts = _seed_accounts(database_url)
    analyst = accounts["Analyst"]
    reviewer = accounts["Reviewer"]
    sip_owner = accounts["SIP Owner"]
    secretariat = accounts["Secretariat"]

    runs = RunRepository(database_url)
    now = datetime.now(UTC)
    coverage_start, coverage_end = _locked_coverage_window(now)

    analyst_http = analyst.session(base_url)
    sip_owner_http = sip_owner.session(base_url)
    reviewer_http = reviewer.session(base_url)
    secretariat_http = secretariat.session(base_url)

    steps: list[dict] = []

    def record(gate: str, via: str, actor: Account, state: RunState) -> None:
        steps.append(
            {
                "gate": gate,
                "via": via,
                "actor": actor.github_login,
                "role": actor.role,
                "now_state": state.value,
            }
        )
        print(f"  [{state.value:<32}] {gate} ({via}, {actor.role})")

    # --- Draft: Analyst creates the run over HTTP -----------------------------------------------
    run_number = f"WALK-{now.strftime('%Y%m%d%H%M%S')}"
    created = _post(
        analyst_http,
        "/api/runs",
        {
            "run_number": run_number,
            "prompt_version": "SIP-050-v1.1",
            "coverage_start_utc": coverage_start,
            "coverage_end_utc": coverage_end,
        },
    )
    run_id = created["id"]
    record("run created", "HTTP POST /api/runs", analyst, RunState.DRAFT)

    # --- Gate 1: Draft -> Run Authorised. SIP Owner authorises, then starts. Both over HTTP. ----
    authorisation = _post(
        sip_owner_http,
        f"/api/runs/{run_id}/authorisations",
        {
            "kind": "Launch",
            "reason": "launch authorised for the #55 walk-through",
            "evidence_ref": "SIP-184 walk-through run record",
            "decided_at": datetime.now(UTC).isoformat(),
        },
    )
    _post(
        sip_owner_http,
        f"/api/runs/{run_id}/start",
        {
            "expected_version": 0,
            "reason": "launch authority recorded",
            "approval_ref": authorisation["id"],
        },
    )
    record(
        "Draft -> Run Authorised",
        "HTTP /authorisations + /start",
        sip_owner,
        RunState.RUN_AUTHORISED,
    )

    # --- Mechanical advances the orchestrator owns: not human gates, driven in-process. --------
    mechanical = [
        (1, RunState.COVERAGE_LOCKED),
        (2, RunState.SCANNING),
        (3, RunState.CANDIDATE_REVIEW),
        (4, RunState.REPORT_DRAFTED),
        (5, RunState.QA_IN_PROGRESS),
    ]
    for version, state in mechanical:
        runs.apply_transition(
            run_id,
            expected_version=version,
            new_state=state,
            actor_id=analyst.user_id,
            reason="mechanical advance (not a gate)",
        )
        record(f"-> {state.value}", "apply_transition", analyst, state)

    # --- Analyst submits the report version over HTTP; streams open on insert. -----------------
    content_sha = hashlib.sha256(run_number.encode()).hexdigest()
    report = _post(
        analyst_http,
        "/api/reports",
        {
            "run_id": run_id,
            "content_sha256": content_sha,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    report_version_id = report["id"]
    steps.append(
        {
            "gate": "report version submitted",
            "via": "HTTP POST /api/reports",
            "actor": analyst.github_login,
            "role": analyst.role,
            "report_version_id": report_version_id,
        }
    )
    print(f"  report version {report['version_number']} submitted by {analyst.role}")

    # --- Reviewer records the SIP-188 QA pass over HTTP. --------------------------------------
    _post(
        reviewer_http,
        f"/api/reports/{report_version_id}/qa",
        {
            "result": "Pass",
            "critical_failures": 0,
            "notes": "walk-through QA pass for #55 evidence; no Critical findings",
        },
    )
    print(f"  QA Pass recorded by {reviewer.role}")

    # --- The three decisions, each over HTTP by its own role. --------------------------------
    ruling = _post(
        sip_owner_http,
        f"/api/reports/{report_version_id}/ruling",
        _decision_body(sip_owner.user_id, "Continue", head_revision=0),
    )
    print(f"  CEO Ruling 'Continue' recorded by {sip_owner.role}")
    _post(
        reviewer_http,
        f"/api/reports/{report_version_id}/approval",
        _decision_body(reviewer.user_id, "Approved", head_revision=0),
    )
    print(f"  Report Approval 'Approved' recorded by {reviewer.role}")
    distribution = _post(
        secretariat_http,
        f"/api/reports/{report_version_id}/distribution",
        _decision_body(
            secretariat.user_id,
            "Authorised",
            head_revision=0,
            distribution_recipient="INZBC members (walk-through, not sent)",
        ),
    )
    print(f"  Distribution Authority 'Authorised' recorded by {secretariat.role}")

    # --- Gate 2: QA In Progress -> Awaiting CEO Decision, pointing at the CEO Ruling record. ---
    runs.apply_transition(
        run_id,
        expected_version=6,
        new_state=RunState.AWAITING_CEO_DECISION,
        actor_id=sip_owner.user_id,
        reason="QA sign-off",
        approval_ref=ruling["id"],
    )
    record(
        "QA In Progress -> Awaiting CEO Decision",
        "apply_transition (CEO Ruling record)",
        sip_owner,
        RunState.AWAITING_CEO_DECISION,
    )

    # --- Gate 3: Awaiting CEO Decision -> Approved for Manual Distribution. ------------------
    runs.apply_transition(
        run_id,
        expected_version=7,
        new_state=RunState.APPROVED_FOR_MANUAL_DISTRIBUTION,
        actor_id=sip_owner.user_id,
        reason="distribution authorised",
        approval_ref=distribution["id"],
    )
    record(
        "Awaiting CEO Decision -> Approved for Manual Distribution",
        "apply_transition (Distribution record)",
        sip_owner,
        RunState.APPROVED_FOR_MANUAL_DISTRIBUTION,
    )

    # --- Gate 4: Approved for Manual Distribution -> Distributed (manual send recorded). ------
    runs.apply_transition(
        run_id,
        expected_version=8,
        new_state=RunState.DISTRIBUTED,
        actor_id=secretariat.user_id,
        reason="manual send recorded",
        approval_ref=distribution["id"],
    )
    record(
        "Approved for Manual Distribution -> Distributed",
        "apply_transition (Distribution record)",
        secretariat,
        RunState.DISTRIBUTED,
    )

    # --- Distributed -> Closed: mechanical closeout, over HTTP. ------------------------------
    _post(
        analyst_http,
        f"/api/runs/{run_id}/complete",
        {
            "expected_version": 9,
            "reason": "walk-through closeout",
        },
    )
    record(
        "Distributed -> Closed",
        "HTTP POST /api/runs/{id}/complete",
        analyst,
        RunState.CLOSED,
    )

    return _evidence(
        database_url, run_id, run_number, report_version_id, accounts, steps
    )


def _evidence(
    database_url: str,
    run_id: str,
    run_number: str,
    report_version_id: str,
    accounts: dict[str, Account],
    steps: list[dict],
) -> dict:
    """Read the durable record back: the run row, every decision_records row for this report
    version, and every audit_log row for this run. This is the artefact #55 asks for.
    """
    with psycopg.connect(database_url, row_factory=psycopg.rows.dict_row) as conn:
        run_row = conn.execute(
            "select id::text, run_number, state, version, production_enabled, "
            "initiated_by::text, analyst_id::text, reviewer_id::text, qa_status, "
            "started_at::text, completed_at::text, created_at::text "
            "from runs where id = %s",
            (run_id,),
        ).fetchone()
        decisions = conn.execute(
            "select id::text, kind, stream_revision, value, actor_id::text, "
            "actor_role_id, decided_at::text, reason from decision_records "
            "where report_version_id = %s order by decided_at",
            (report_version_id,),
        ).fetchall()
        audit = conn.execute(
            "select id, at::text, user_id::text, action, record_type, record_id, "
            "old_value, new_value, reason, approval_ref from audit_log "
            "where record_id = %s order by id",
            (run_id,),
        ).fetchall()
    return {
        "disclaimer": "Walk-through for #55 evidence. NOT a SIP-184 production run - SIP-191's "
        "launch window expired 31 Jul 2026. production_enabled is false.",
        "generated_at": datetime.now(UTC).isoformat(),
        "run_number": run_number,
        "accounts": {
            a.role: {"github_login": a.github_login, "user_id": a.user_id}
            for a in accounts.values()
        },
        "steps": steps,
        "run_row": run_row,
        "decision_records": decisions,
        "audit_log": audit,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--database-url", default=None, help="defaults to $DATABASE_URL"
    )
    parser.add_argument("--evidence-out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import os

    args = _parse_args(argv)
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL is not set and --database-url was not given", file=sys.stderr
        )
        return 2

    print(
        f"[walk] taking one run Draft -> Distributed -> Closed against {args.base_url}"
    )
    evidence = run_walk(args.base_url, database_url)

    final_state = evidence["run_row"]["state"]
    print(f"\n[walk] run {evidence['run_number']} finished in state {final_state!r}")
    print(
        f"[walk] {len(evidence['decision_records'])} decision records, "
        f"{len(evidence['audit_log'])} audit rows"
    )
    if final_state != RunState.CLOSED.value:
        print("[walk] run did not reach Closed", file=sys.stderr)
        return 1

    if args.evidence_out:
        args.evidence_out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"[walk] evidence written to {args.evidence_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
