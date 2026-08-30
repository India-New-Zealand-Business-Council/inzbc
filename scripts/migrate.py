"""Forward-only SQL migration runner (#44).

`database/schema.sql` is the baseline. Every change after it is an ordered file in
`database/migrations/`, applied once, in filename order, each inside its own transaction.

No new dependency. The repository already talks to Postgres through raw psycopg and raw SQL, so a
migration tool that brings SQLAlchemy with it would add a dependency to solve a problem that a
tracking table and a loop already solve.

Forward-only on purpose. A "down" migration is written and never run, so it is never tested, and
an untested rollback is worse than no rollback because it invites you to trust it. To undo a
migration, write the next one.

Usage:

    DATABASE_URL=... python scripts/migrate.py status     # what is applied, what is pending
    DATABASE_URL=... python scripts/migrate.py up         # apply everything pending
    DATABASE_URL=... python scripts/migrate.py baseline   # record an already-built database

`baseline` exists for databases created by running schema.sql directly, which is every database
that existed before this script. It records the baseline as applied *without* re-running it.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "database" / "schema.sql"
MIGRATIONS = REPO_ROOT / "database" / "migrations"
BASELINE = "0000_baseline_schema.sql"

# One session-level lock id, so two runners on the same database serialise instead of racing.
# Arbitrary constant; it only has to be stable and unlikely to collide with another advisory user.
LOCK_ID = 8_142_026

TRACKING_TABLE = """
create table if not exists schema_migrations (
  filename    text primary key,
  checksum    text not null,
  applied_at  timestamptz not null default now()
)
"""


def checksum(text: str) -> str:
    # Newlines normalised so a checkout with CRLF endings does not read as a changed migration.
    return hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()[:16]


def pending_files() -> list[Path]:
    if not MIGRATIONS.is_dir():
        return []
    return sorted(p for p in MIGRATIONS.glob("*.sql"))


def applied(conn: psycopg.Connection) -> dict[str, str]:
    conn.execute(TRACKING_TABLE)
    conn.commit()
    return {
        row[0]: row[1]
        for row in conn.execute("select filename, checksum from schema_migrations").fetchall()
    }


def verify_baseline(done: dict[str, str]) -> None:
    """Refuses to proceed if schema.sql changed after being recorded as the baseline.

    Without this the two sources of truth drift silently: a database built today from schema.sql
    and one built last month from schema.sql plus migrations would differ, and nothing would say
    so. Editing the baseline is the mistake this catches - the fix is a new migration file.
    """
    if BASELINE not in done:
        return
    current = checksum(SCHEMA.read_text(encoding="utf-8"))
    if current != done[BASELINE]:
        raise SystemExit(
            f"refusing: database/schema.sql has changed since it was recorded as the baseline\n"
            f"  recorded: {done[BASELINE]}\n"
            f"  current:  {current}\n"
            f"schema.sql is immutable once baselined. Add a file to database/migrations/ instead.\n"
            f"\n"
            f"If the change IS already in this database - the usual case, since schema.sql is kept\n"
            f"as the current full picture alongside each migration - re-record the checksum:\n"
            f"    python scripts/migrate.py rebaseline\n"
            f"That updates the recorded checksum and runs no SQL. Confirm the change reached this\n"
            f"database first; rebaselining a database that is genuinely behind hides the gap."
        )


def cmd_status(conn: psycopg.Connection) -> int:
    done = applied(conn)
    print(f"baseline: {'applied' if BASELINE in done else 'NOT APPLIED'}")
    files = pending_files()
    if not files:
        print("migrations: none on disk")
    for path in files:
        state = "applied" if path.name in done else "pending"
        print(f"  {path.name}: {state}")
    if BASELINE in done:
        current = checksum(SCHEMA.read_text(encoding="utf-8"))
        drift = "" if current == done[BASELINE] else "  <-- CHANGED since baseline"
        print(f"schema.sql checksum: {current}{drift}")
    return 0


def cmd_baseline(conn: psycopg.Connection) -> int:
    done = applied(conn)
    if BASELINE in done:
        print("baseline already recorded")
        return 0
    # schema_migrations is excluded because applied() has already created it by this point, so an
    # empty database reports one table and the guard below never fires. Counting our own
    # bookkeeping table as evidence the schema exists let a genuinely empty database be recorded
    # as baselined, which would then silently skip the entire schema on the next `up`.
    tables = conn.execute(
        "select count(*) from information_schema.tables "
        "where table_schema = 'public' and table_name <> 'schema_migrations'"
    ).fetchone()[0]
    if tables == 0:
        raise SystemExit(
            "refusing: this database is empty, so there is nothing to baseline.\n"
            "Apply database/schema.sql first, then run baseline."
        )
    conn.execute(
        "insert into schema_migrations (filename, checksum) values (%s, %s)",
        (BASELINE, checksum(SCHEMA.read_text(encoding="utf-8"))),
    )
    conn.commit()
    print(f"recorded {BASELINE} as applied ({tables} tables already present, none re-run)")
    return 0


def cmd_rebaseline(conn: psycopg.Connection) -> int:
    """Re-records schema.sql's checksum. Runs no SQL.

    The drift guard was written without a way out, which made it a trap rather than a control:
    `schema.sql` is deliberately kept as the current full picture and updated in the same pull
    request as each migration, so every migration makes the recorded checksum stale and `up`
    refused permanently on every already-baselined database. Adversarial review caught it.

    Kept as a separate, explicitly-named command rather than something `up` does silently, because
    the one case where the refusal is right - the database really is missing the change - is
    exactly the case where a silent fix would hide it.
    """
    done = applied(conn)
    if BASELINE not in done:
        raise SystemExit("refusing: no baseline recorded, so there is nothing to rebaseline.")
    current = checksum(SCHEMA.read_text(encoding="utf-8"))
    if current == done[BASELINE]:
        print("schema.sql checksum already matches; nothing to do")
        return 0
    conn.execute(
        "update schema_migrations set checksum = %s where filename = %s", (current, BASELINE)
    )
    conn.commit()
    print(f"rebaselined: {done[BASELINE]} -> {current} (no SQL run)")
    return 0


def cmd_up(conn: psycopg.Connection) -> int:
    done = applied(conn)
    verify_baseline(done)
    if BASELINE not in done:
        raise SystemExit(
            "refusing: no baseline recorded.\n"
            "For a new database: apply database/schema.sql, then run `migrate.py baseline`.\n"
            "For an existing one: run `migrate.py baseline`."
        )

    # Serialise concurrent runners. Session-level rather than transaction-level because each
    # migration commits separately, and the lock has to outlive those commits.
    conn.execute("select pg_advisory_lock(%s)", (LOCK_ID,))
    try:
        done = applied(conn)
        count = 0
        for path in pending_files():
            if path.name in done:
                sql = path.read_text(encoding="utf-8")
                if checksum(sql) != done[path.name]:
                    raise SystemExit(
                        f"refusing: {path.name} was modified after it was applied.\n"
                        f"An applied migration is immutable. Write a new one instead."
                    )
                continue
            sql = path.read_text(encoding="utf-8")
            print(f"applying {path.name} ...", end=" ", flush=True)
            # Each migration is its own transaction: a failure leaves earlier ones applied and
            # this one fully rolled back, rather than a half-migrated database.
            try:
                conn.execute(sql)
                conn.execute(
                    "insert into schema_migrations (filename, checksum) values (%s, %s)",
                    (path.name, checksum(sql)),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                print("FAILED (rolled back)")
                raise
            print("ok")
            count += 1
        print(f"{count} migration(s) applied" if count else "nothing to apply")
    finally:
        conn.execute("select pg_advisory_unlock(%s)", (LOCK_ID,))
        conn.commit()
    return 0


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    commands = {
        "status": cmd_status,
        "up": cmd_up,
        "baseline": cmd_baseline,
        "rebaseline": cmd_rebaseline,
    }
    if command not in commands:
        print(f"unknown command {command!r}; expected one of {', '.join(commands)}", file=sys.stderr)
        return 1
    with psycopg.connect(url, autocommit=False) as conn:
        return commands[command](conn)


if __name__ == "__main__":
    raise SystemExit(main())
