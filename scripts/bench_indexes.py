"""Measure whether the schema's foreign-key columns need indexes (#334).

Seeds a realistic volume into a throwaway database, runs the query shapes that
`services/api` actually issues, and reports the planner's choice and timing before and after the
candidate indexes are created.

The point is that an index with no measurement behind it is a guess. Every index proposed in #334
has to earn its place here first: if the plan does not change and the timing does not improve, the
index is not worth the write cost and does not get added.

Run against a scratch database, never the demo one:

    DATABASE_URL=postgresql://inzbc:inzbc@localhost:5432/inzbc_bench \
        .venv/Scripts/python.exe scripts/bench_indexes.py

The schema must already be applied to that database.
"""

from __future__ import annotations

import os
import sys
import uuid

import psycopg

# Volume seeded before measuring. Small enough to run in under a minute, large enough that a
# sequential scan and an index scan are visibly different - at the ~500 rows the demo database
# carries, Postgres correctly ignores an index and the comparison says nothing.
RUNS = 200
CANDIDATES_PER_RUN = 250
AUDIT_ROWS = 40_000

# Candidate indexes, each tied to the query it serves. An entry with no named query does not
# belong here - that is the rule the issue sets, and it is enforced by this list being the only
# input to the "after" pass.
CANDIDATE_INDEXES = [
    (
        "candidates_run_id_idx",
        "create index candidates_run_id_idx on candidates (run_id)",
        "select ... from candidates where run_id = %s  (15 query sites in services/api)",
    ),
    (
        "candidates_run_verification_idx",
        "create index candidates_run_verification_idx on candidates (run_id, verification)",
        "select ... from candidates where run_id = %s group by verification",
    ),
    (
        "audit_log_record_idx",
        "create index audit_log_record_idx on audit_log (record_type, record_id, at desc)",
        "audit trail lookup for one record, newest first",
    ),
]

# Deliberately NOT proposed, and the reason, so nobody re-proposes them later:
#
#   source_checks (run_id, source_id) - already backed by the UNIQUE constraint
#       source_checks_run_id_source_id_key. Postgres creates an index for every PRIMARY KEY and
#       UNIQUE constraint, so the column pair is already covered.
#   report_versions (run_id) - already covered as the leading column of the UNIQUE constraint
#       report_versions_run_id_version_number_key. A leading-column prefix serves
#       `where run_id = ?` without a second index.
#
# This matters more generally: `grep -c '^create index' database/schema.sql` returns 3, but
# `select count(*) from pg_indexes where schemaname='public'` returns 51. Counting only explicit
# CREATE INDEX statements understates the schema's real index coverage by 48.

# The shapes measured. Kept literal rather than parameterised so the plan text is stable and
# comparable between passes.
QUERIES = [
    ("candidates by run", "select * from candidates where run_id = %(run)s"),
    (
        "candidate verification rollup",
        "select verification, count(*) from candidates where run_id = %(run)s group by verification",
    ),
    (
        "source check lookup (already covered by UNIQUE)",
        "select * from source_checks where run_id = %(run)s and source_id = %(source)s",
    ),
    (
        "audit trail for one record",
        "select * from audit_log where record_type = 'run' and record_id = %(run)s order by at desc limit 50",
    ),
    (
        "report versions by run",
        "select * from report_versions where run_id = %(run)s order by version_number desc",
    ),
]


def seed(conn: psycopg.Connection) -> tuple[str, str]:
    """Fills the scratch database and returns a run id and source id to query against."""
    with conn.cursor() as cur:
        cur.execute("select count(*) from runs")
        if cur.fetchone()[0] >= RUNS:
            cur.execute("select id from runs limit 1")
            run = str(cur.fetchone()[0])
            cur.execute("select id from source_library limit 1")
            row = cur.fetchone()
            return run, str(row[0]) if row else str(uuid.uuid4())

        user_id = str(uuid.uuid4())
        cur.execute(
            "insert into users (id, name, email, github_login, active) "
            "values (%s, %s, %s, %s, true)",
            (user_id, "Bench User", "bench@example.invalid", "bench-user"),
        )
        source_id = str(uuid.uuid4())
        cur.execute(
            "insert into source_library (id, sip185_code, name, layer, mandatory, base_url) "
            "values (%s, %s, %s, 1, true, %s)",
            (source_id, "BENCH-001", "Bench Source", "https://example.invalid"),
        )

        run_ids = []
        for i in range(RUNS):
            rid = str(uuid.uuid4())
            run_ids.append(rid)
            cur.execute(
                "insert into runs (id, run_number, coverage_start_utc, coverage_end_utc, "
                "state, prompt_version, initiated_by) "
                "values (%s, %s, now() - interval '1 day', now(), 'Draft', 'v1.1', %s)",
                (rid, f"BENCH-{i:05d}", user_id),
            )
        conn.commit()

        # Executemany rather than one statement per row so the seed stays under a minute at 50k
        # rows. verification is an enum - 'Unverified' is the schema's own default label.
        rows = [
            (str(uuid.uuid4()), rid, source_id, f"Headline {n}", user_id, "Unverified")
            for rid in run_ids
            for n in range(CANDIDATES_PER_RUN)
        ]
        cur.executemany(
            "insert into candidates (id, run_id, source_id, headline, captured_by, verification) "
            "values (%s, %s, %s, %s, %s, %s)",
            rows,
        )
        conn.commit()

        # audit_log.id is a bigint identity column, so it is not supplied here.
        audit = [
            (user_id, "bench.event", "run", run_ids[n % len(run_ids)])
            for n in range(AUDIT_ROWS)
        ]
        cur.executemany(
            "insert into audit_log (user_id, action, record_type, record_id) "
            "values (%s, %s, %s, %s)",
            audit,
        )

        # source_checks and report_versions are seeded too, because an index measured against an
        # empty table produces a 0.01ms "no gain" result that looks like evidence and is not.
        # One row per (run, source): source_checks carries a UNIQUE constraint on that pair, which
        # is itself the reason no extra index is proposed for it.
        cur.executemany(
            "insert into source_checks (id, run_id, source_id, outcome) values (%s, %s, %s, %s)",
            [(str(uuid.uuid4()), rid, source_id, "Included") for rid in run_ids],
        )
        cur.execute("select id from roles limit 1")
        row = cur.fetchone()
        role_id = row[0] if row else None
        if role_id is not None:
            cur.executemany(
                "insert into report_versions (id, run_id, version_number, created_by, "
                "created_by_role_id, content_sha256, created_at) "
                "values (%s, %s, %s, %s, %s, %s, now())",
                [
                    (str(uuid.uuid4()), rid, v + 1, user_id, role_id, f"{'0' * 64}")
                    for rid in run_ids
                    for v in range(10)
                ],
            )
        conn.commit()
        return run_ids[0], source_id


def measure(conn: psycopg.Connection, run: str, source: str) -> dict[str, tuple[str, float]]:
    """Returns {label: (scan type, execution ms)} for each query shape."""
    out: dict[str, tuple[str, float]] = {}
    with conn.cursor() as cur:
        for label, sql in QUERIES:
            cur.execute(
                f"explain (analyze, buffers, format text) {sql}",
                {"run": run, "source": source},
            )
            plan = "\n".join(r[0] for r in cur.fetchall())
            scan = "Seq Scan" if "Seq Scan" in plan.split("\n")[0] else "Index/other"
            for line in plan.splitlines():
                if "Seq Scan" in line:
                    scan = "Seq Scan"
                    break
                if "Index Scan" in line or "Bitmap" in line:
                    scan = "Index Scan"
                    break
            ms = 0.0
            for line in plan.splitlines():
                if "Execution Time" in line:
                    ms = float(line.split(":")[1].strip().split(" ")[0])
            out[label] = (scan, ms)
    return out


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    # Refuse to seed 50k rows into the demo or a real database by accident.
    if "bench" not in url:
        print(f"refusing: DATABASE_URL must name a bench database, got {url!r}", file=sys.stderr)
        return 1

    with psycopg.connect(url) as conn:
        print(f"seeding: {RUNS} runs, {RUNS * CANDIDATES_PER_RUN} candidates, {AUDIT_ROWS} audit rows")
        run, source = seed(conn)
        with conn.cursor() as cur:
            cur.execute("analyze")
        conn.commit()

        before = measure(conn, run, source)

        with conn.cursor() as cur:
            for name, ddl, _ in CANDIDATE_INDEXES:
                cur.execute(f"select to_regclass('{name}')")
                if cur.fetchone()[0] is None:
                    cur.execute(ddl)
            cur.execute("analyze")
        conn.commit()

        after = measure(conn, run, source)

    print(f"\n{'query':<32} {'before':<26} {'after':<26} {'change':<10}")
    print("-" * 96)
    for label, _ in QUERIES:
        b_scan, b_ms = before[label]
        a_scan, a_ms = after[label]
        delta = f"{(1 - a_ms / b_ms) * 100:5.1f}% faster" if b_ms and a_ms < b_ms else "no gain"
        print(f"{label:<32} {b_scan + f' {b_ms:.2f}ms':<26} {a_scan + f' {a_ms:.2f}ms':<26} {delta:<10}")

    print("\nindexes measured:")
    for name, _, why in CANDIDATE_INDEXES:
        print(f"  {name}\n      serves: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
