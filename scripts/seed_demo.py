"""Seed a local demo database with a run and candidates worth showing (#135 support).

Demo data only, and it says so in the data itself: the run is numbered `DEMO-...` rather than
`RUN-...`, exactly as `run_dry_run.py` stamps `DRYRUN-`, so a demo row can never be mistaken for
an authorised production run if this database is ever pointed at something real.

Two users, not one, because the platform refuses self-verification: the analyst who captures a
candidate cannot verify it, and the reviewer who verifies cannot then score it. A single-user
seed would be unable to produce a verified candidate at all, which is the control working.

Run against a scratch database only:

    DATABASE_URL=postgresql://inzbc:inzbc@localhost:5432/inzbc_demo \
      .venv/Scripts/python.exe -m scripts.seed_demo
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

from services.api.tests.role_seed import role_id

ANALYST_LOGIN = "demo-analyst"
REVIEWER_LOGIN = "demo-reviewer"


def _user(conn, *, login: str, name: str, roles: tuple[str, ...]) -> str:
    row = conn.execute(
        "insert into users (name, email, github_login) values (%s, %s, %s) "
        "on conflict (github_login) do update set name = excluded.name returning id",
        (name, f"{login}@example.test", login),
    ).fetchone()
    user_id = row["id"]
    for role in roles:
        # `role_id` creates the role if the table is empty, which it is in a database built from
        # `schema.sql` alone: the schema defines `roles` but seeds no rows. An earlier version
        # selected from `roles` by name and silently granted nothing on a fresh database, so
        # `dev_session` issued a session with no roles and every business route refused it.
        # Reused from the test helper rather than reimplemented, so demo and test seeds cannot
        # disagree about which id a role name lives at.
        conn.execute(
            "insert into user_roles (user_id, role_id, enabled) values (%s, %s, true) "
            "on conflict (user_id, role_id) do update set enabled = true",
            (user_id, role_id(conn, role)),
        )
    return str(user_id)


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    if "inzbc_demo" not in url:  # matches inzbc_demo and inzbc_demo2
        # A guard, not a formality: this writes rows and must never be aimed at a real database.
        print(f"refusing: DATABASE_URL must name a demo database, got {url!r}", file=sys.stderr)
        return 2

    now = datetime.now(UTC)
    with psycopg.connect(url, row_factory=dict_row) as conn:
        analyst = _user(conn, login=ANALYST_LOGIN, name="Demo Analyst", roles=("Analyst",))
        reviewer = _user(
            conn, login=REVIEWER_LOGIN, name="Demo Reviewer", roles=("Reviewer", "SIP Owner")
        )

        run = conn.execute(
            "insert into runs (run_number, prompt_version, coverage_start_utc, coverage_end_utc, "
            "initiated_by, analyst_id, reviewer_id, state, started_at) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id, run_number",
            (
                # Timestamped to the second, not the day: re-running the seed after a partial
                # failure otherwise collides with `runs_run_number_key` and aborts. `runs` is
                # append-only by design, so the fix is a fresh number rather than a delete.
                f"DEMO-{now.strftime('%Y%m%d-%H%M%S')}",
                "SIP-050 v1.1",
                now - timedelta(days=1),
                now,
                analyst,
                analyst,
                reviewer,
                "Candidate Review",
                now - timedelta(hours=3),
            ),
        ).fetchone()
        run_id = run["id"]

        # Headlines are plausible but invented, and the run number says DEMO so nothing here can
        # be read as real collected intelligence.
        candidates = [
            ("NZ and India conclude FTA ratification timetable", "Verified", 5, 5, "High"),
            ("Wool exporters weigh day-one tariff elimination", "Verified", 4, 3, "Medium"),
            ("Auckland delegation to Mumbai confirmed for October", "Partially Verified", 3, 4, "Medium"),
            ("Unconfirmed report of dairy quota review", "Unverified", 2, 2, None),
        ]
        for headline, verification, nz, member, signal in candidates:
            cand = conn.execute(
                "insert into candidates (run_id, headline, url, summary, in_coverage_window, "
                "captured_by) values (%s, %s, %s, %s, true, %s) returning id",
                (run_id, headline, "https://example.test/demo", "Demo summary.", analyst),
            ).fetchone()
            if verification != "Unverified":
                # Verified by the reviewer, never the capturer: the platform refuses that, and a
                # seed that worked around it would be seeding a state the product cannot reach.
                conn.execute(
                    "update candidates set verification = %s, verified_by = %s where id = %s",
                    (verification, reviewer, cand["id"]),
                )
            conn.execute(
                "update candidates set nz_relevance = %s, member_relevance = %s, signal = %s, "
                "assessed_by = %s where id = %s",
                (nz, member, signal, analyst, cand["id"]),
            )
        conn.commit()

    print(f"run:      {run['run_number']} ({run_id})")
    print(f"analyst:  {ANALYST_LOGIN}")
    print(f"reviewer: {REVIEWER_LOGIN}")
    print(f"candidates: {len(candidates)}")
    print()
    print("Issue a session with:")
    print(f"  python -m scripts.dev_session --github-login {REVIEWER_LOGIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
