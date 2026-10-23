"""Replay and tamper detection through the database, not just in memory.

`replay_fidelity.py` measures replay on audit logs held in memory. In production a trail is
written to Postgres (`agent_rehearsals`, migration 0007) and read back before it is verified, so
two further questions matter:

1. **Round trip.** Does a sealed, signed trail come back from the database exactly, and still
   replay to the same state under its seal?
2. **Tampering at the database.** The table is append-only by trigger and the application role
   has INSERT and SELECT only. Someone with database owner rights can still switch triggers off
   (`session_replication_role = replica`) and rewrite a row. Is that caught when the trail is
   next read and verified?

Same seeded runs as `replay_fidelity` (seed 20261024). Needs a Postgres with `database/schema.sql`
loaded and a `DATABASE_URL` whose role may set `session_replication_role` (an owner or superuser,
as an attacker with database access would be); no model is called:

    DATABASE_URL=postgresql://... uv run python -m apps.sip.core.eval.persisted_replay --write
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from apps.sip.core.agent_loop import replay_agent_audit
from apps.sip.core.agent_record import audit_from_json, audit_to_json
from apps.sip.core.audit_seal import audit_chain_head
from apps.sip.core.eval._fixtures import (
    MEASUREMENT_KEY,
    redaction_policy,
    source_lookup,
)
from apps.sip.core.eval.replay_fidelity import (
    DEFAULT_RUNS,
    DEFAULT_SEED,
    execute,
    generate,
    normalised,
)
from services.api.agent_rehearsals import AgentRehearsalRepository
from services.api.persistence import RunRepository

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _first_gated(audit: dict) -> dict | None:
    return next((t for t in audit["transitions"] if t["human_decision"]), None)


def _forge_approver(audit: dict) -> bool:
    gated = _first_gated(audit)
    if gated is None:
        return False
    gated["human_decision"]["approver"] = "Forged approver"
    return True


def _raise_signal(audit: dict) -> bool:
    for candidate in audit["candidates"]:
        if candidate.get("signal") not in ("High", "Critical"):
            candidate["signal"] = "Critical"
            return True
    return False


def _drop_last_record(audit: dict) -> bool:
    if not audit["tool_records"]:
        return False
    audit["tool_records"].pop()
    return True


def _skip_to_ceo(audit: dict) -> bool:
    last = audit["transitions"][-1]
    audit["transitions"].append({
        "from_state": last["to_state"], "to_state": "Awaiting CEO Decision", "actor": "sip-agent",
        "at": last["at"], "human_decision": {"approver": "QA Reviewer", "decision": "QA pass",
                                             "note": None, "signature": None},
    })
    return True


def _edit_reason(audit: dict) -> bool:
    if not audit["tool_records"]:
        return False
    audit["tool_records"][0]["reason"] = "Rewritten after the fact."
    return True


# (name, safety-relevant, mutation). Each rewrites the stored JSON in place and recomputes the
# stored chain head to match, as an attacker with write access would; only the seal, made with a
# key the database never holds, is left as it was.
MUTATIONS: tuple[tuple[str, bool, Callable[[dict], bool]], ...] = (
    ("forge-human-approver", True, _forge_approver),
    ("raise-candidate-to-critical", True, _raise_signal),
    ("drop-last-tool-record", True, _drop_last_record),
    ("append-ungated-ceo-transition", True, _skip_to_ceo),
    ("edit-a-reason", False, _edit_reason),
)


def _detected(stored: dict, seal: str | None, *, keyed: bool = True) -> bool:
    """True when reading the row back and verifying it refuses, as `verify()` does on every read.

    `keyed=False` verifies as a deployment without `SIP_DECISION_SIGNING_KEY` would: chain and
    replay rules only, no seal or signature check. It shows what the key itself adds.
    """
    try:
        audit = audit_from_json(stored)
        if keyed:
            replay_agent_audit(audit, source_id_lookup=source_lookup(), signing_key=MEASUREMENT_KEY, seal=seal)
        else:
            replay_agent_audit(audit, source_id_lookup=source_lookup())
    except Exception:  # noqa: BLE001 - any refusal is detection
        return True
    return False


def run_measurement(database_url: str, runs: int = DEFAULT_RUNS, seed: int = DEFAULT_SEED) -> dict[str, object]:
    repo = AgentRehearsalRepository(database_url)
    with psycopg.connect(database_url) as conn:
        actor = str(conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Persisted replay {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()[0])
        conn.commit()
    run_id = RunRepository(database_url).create_run(
        run_number=f"RUN-PERSIST-{uuid.uuid4().hex[:10]}", prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00", coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=actor,
    ).id

    round_trip = replay_after_read = app_update_refused = 0
    tamper = {
        name: {"safety_relevant": relevant, "applied": 0, "detected": 0, "detected_without_key": 0}
        for name, relevant, _ in MUTATIONS
    }
    with redaction_policy():
        for index in range(runs):
            agent = execute(generate(seed, index), key=MEASUREMENT_KEY)
            audit, seal = agent.sealed_audit_log(MEASUREMENT_KEY)
            record = repo.record(
                run_id=run_id, started_by=actor,
                outcome="reached_qa" if agent.state.value == "QA In Progress" else "stopped",
                stop_reason=None if agent.state.value == "QA In Progress" else f"stopped at {agent.state.value}",
                final_state=agent.state.value, steps=len(audit.tool_records),
                audit=audit_to_json(audit), chain_head=audit_chain_head(audit), seal=seal,
            )
            read = repo.get(run_id, record.id)
            restored = audit_from_json(read.audit)
            round_trip += int(normalised(restored) == normalised(audit) and read.seal == seal)
            # A genuine trail that fails to replay after storage is the finding, so it is counted
            # by not incrementing rather than raised.
            replay_after_read += int(not _detected(read.audit, read.seal)
                                     and replay_agent_audit(restored, source_id_lookup=source_lookup(),
                                                            signing_key=MEASUREMENT_KEY,
                                                            seal=read.seal).state is agent.state)

            # The application's own path cannot rewrite the row: the trigger refuses.
            with psycopg.connect(database_url) as conn:
                try:
                    conn.execute("update agent_rehearsals set steps = steps + 1 where id = %s", (record.id,))
                    conn.commit()
                except psycopg.Error:
                    conn.rollback()
                    app_update_refused += 1

            for name, _relevant, mutation in MUTATIONS:
                stored = json.loads(json.dumps(read.audit))
                if not mutation(stored):
                    continue
                try:
                    chain = audit_chain_head(audit_from_json(stored))
                except Exception:  # noqa: BLE001 - a row the reader cannot even parse is caught
                    chain = read.chain_head
                with psycopg.connect(database_url) as conn:
                    conn.execute("set session_replication_role = replica")
                    conn.execute(
                        "update agent_rehearsals set audit = %s, chain_head = %s where id = %s",
                        (Jsonb(stored), chain, record.id),
                    )
                    conn.commit()
                tampered = repo.get(run_id, record.id)
                tamper[name]["applied"] += 1
                tamper[name]["detected"] += int(_detected(tampered.audit, tampered.seal))
                tamper[name]["detected_without_key"] += int(_detected(tampered.audit, None, keyed=False))
                with psycopg.connect(database_url) as conn:
                    conn.execute("set session_replication_role = replica")
                    conn.execute(
                        "update agent_rehearsals set audit = %s, chain_head = %s where id = %s",
                        (Jsonb(read.audit), read.chain_head, record.id),
                    )
                    conn.commit()

    def total(relevant: bool) -> tuple[int, int]:
        rows = [row for row in tamper.values() if row["safety_relevant"] is relevant]
        return sum(r["detected"] for r in rows), sum(r["applied"] for r in rows)

    safety_detected, safety_applied = total(True)
    safety_without_key = sum(r["detected_without_key"] for r in tamper.values() if r["safety_relevant"])
    meta_detected, meta_applied = total(False)
    return {
        "runs": runs,
        "seed": seed,
        "round_trip_exact": round_trip,
        "replay_exact_after_read": replay_after_read,
        "application_update_refused": app_update_refused,
        "db_tamper_safety_detected": safety_detected,
        "db_tamper_safety_applied": safety_applied,
        "db_tamper_safety_detected_without_key": safety_without_key,
        "db_tamper_metadata_detected": meta_detected,
        "db_tamper_metadata_applied": meta_applied,
        "db_tamper_by_mutation": tamper,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--write", action="store_true", help="save results/persisted-replay.json")
    args = parser.parse_args(argv)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(json.dumps({"status": "not-run", "reason": "needs DATABASE_URL with schema.sql loaded"}))
        return 0
    report = {"status": "measured", **run_measurement(database_url, args.runs)}
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered, end="")
    if args.write:
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "persisted-replay.json").write_text(rendered, encoding="utf-8")
    ok = (report["round_trip_exact"] == report["runs"] and report["replay_exact_after_read"] == report["runs"]
          and report["db_tamper_safety_detected"] == report["db_tamper_safety_applied"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
