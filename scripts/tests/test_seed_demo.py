"""Integration tests for `scripts/seed_demo.py` (#338), against a real Postgres.

Skipped entirely when `DATABASE_URL` isn't set, matching every other integration suite in this
repository (`services/api/tests/test_persistence.py` et al.) — a mock would prove this script
calls psycopg correctly, not that the seeded data actually satisfies the schema's constraints
(the append-only triggers, the SoD checks, the state-machine gates), which is the entire point of
running it against a real database rather than reading the code and trusting it.

`main()` runs once per test session (`_seeded` is session-scoped): the script takes real work to
run (~700 source-check inserts alone), and every test here only asserts on state it leaves behind,
so there is nothing to gain from re-running it per test — `test_main_is_idempotent_on_rerun` below
is the one test that deliberately calls it a second time, to prove reruns don't duplicate rows.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from psycopg.rows import dict_row

from scripts import seed_demo

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - seed_demo tests need a real Postgres with schema.sql applied",
)


def _connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@pytest.fixture(scope="session")
def _seeded() -> None:
    """Runs the seed script once for the whole test session."""
    assert seed_demo.main() == 0
