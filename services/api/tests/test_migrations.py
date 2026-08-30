"""The migration runner's refusals (#44).

Only the guards are tested here, not the happy path: "it applied the SQL" is visible the moment
anyone runs it, whereas a guard that silently stops guarding is not. Each of these refusals exists
because the alternative is a database that is quietly wrong.

The baseline-on-empty case is a regression test. It shipped broken: `applied()` creates
`schema_migrations` before the emptiness check counts tables, so an empty database reported one
table and was happily recorded as baselined - which would then skip the entire schema forever.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

DATABASE_URL = os.getenv("DATABASE_URL", "")
REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATE = REPO_ROOT / "scripts" / "migrate.py"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set - migration tests need a real Postgres"
)


def run(database_url: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MIGRATE), *args],
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        # Non-zero is the expected outcome for most of these - the refusals are what is under
        # test, so a raise here would fail the tests that are working correctly.
        check=False,
    )


@pytest.fixture
def empty_database() -> str:
    """A throwaway database with no schema applied.

    Created and left behind rather than dropped: this suite has no authority to drop anything, and
    a handful of small empty databases on a dev machine is a cheaper problem than a DROP running
    somewhere it should not.
    """
    name = f"migtest_{uuid.uuid4().hex[:12]}"
    admin = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'create database "{name}"')
    return DATABASE_URL.rsplit("/", 1)[0] + f"/{name}"


def test_up_refuses_without_a_baseline(empty_database: str) -> None:
    result = run(empty_database, "up")
    assert result.returncode != 0
    assert "no baseline recorded" in result.stdout + result.stderr


def test_baseline_refuses_an_empty_database(empty_database: str) -> None:
    """The bookkeeping table must not count as evidence the schema exists."""
    result = run(empty_database, "baseline")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "this database is empty" in combined
    # The specific failure mode: reporting a table count of 1 (schema_migrations) and proceeding.
    assert "1 tables already present" not in combined


def test_baseline_then_up_applies_migrations(empty_database: str) -> None:
    schema = (REPO_ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(empty_database, autocommit=True) as conn:
        conn.execute(schema)

    assert run(empty_database, "baseline").returncode == 0
    first = run(empty_database, "up")
    assert first.returncode == 0, first.stdout + first.stderr

    # Idempotent: a second run applies nothing rather than failing or re-running.
    second = run(empty_database, "up")
    assert second.returncode == 0
    assert "nothing to apply" in second.stdout


def test_baseline_is_recorded_without_rerunning_the_schema(empty_database: str) -> None:
    """`baseline` must record, never execute - re-running schema.sql would error on every object."""
    schema = (REPO_ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(empty_database, autocommit=True) as conn:
        conn.execute(schema)
    result = run(empty_database, "baseline")
    assert result.returncode == 0
    assert "none re-run" in result.stdout
