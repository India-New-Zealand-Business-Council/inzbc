"""Checks that models.py's enums exactly match database/schema.sql's enum definitions.

This is the one thing about the pipeline module that's verifiable without a live server or
database: that the contract mirror hasn't drifted from the source of truth. If this fails, either
models.py needs updating or database/schema.sql changed and the pipeline needs to catch up.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from apps.sip.pipeline.models import (
    RunState,
    SignalStrength,
    SourceConfidence,
    SourceOutcome,
    VerificationState,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "database" / "schema.sql"

# Maps each Postgres enum type (schema.sql) to the Python Enum that mirrors it (models.py).
# Only the enums the pipeline module actually uses are checked here — approval_state and
# distribution_state belong to Paras's control-side module, not this one.
ENUM_MIRRORS = {
    "signal_strength": SignalStrength,
    "source_confidence": SourceConfidence,
    "source_outcome": SourceOutcome,
    "verification_state": VerificationState,
    "run_state": RunState,
}


def _parse_sql_enums(sql_text: str) -> dict[str, list[str]]:
    enums = {}
    for match in re.finditer(
        r"create type (\w+)\s+as enum\s*\((.*?)\)", sql_text, re.IGNORECASE | re.DOTALL
    ):
        type_name, body = match.group(1), match.group(2)
        values = re.findall(r"'([^']*)'", body)
        enums[type_name] = values
    return enums


@pytest.fixture(scope="module")
def sql_enums() -> dict[str, list[str]]:
    assert SCHEMA_PATH.exists(), f"expected schema at {SCHEMA_PATH}"
    return _parse_sql_enums(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_has_every_mirrored_enum(sql_enums: dict[str, list[str]]) -> None:
    missing = set(ENUM_MIRRORS) - set(sql_enums)
    assert not missing, f"database/schema.sql no longer defines: {missing}"


@pytest.mark.parametrize("sql_type_name,python_enum", ENUM_MIRRORS.items())
def test_enum_values_match(sql_enums, sql_type_name, python_enum) -> None:
    sql_values = sql_enums[sql_type_name]
    python_values = [member.value for member in python_enum]
    assert python_values == sql_values, (
        f"{python_enum.__name__} in models.py does not match `{sql_type_name}` in "
        f"database/schema.sql.\n  schema.sql: {sql_values}\n  models.py:  {python_values}"
    )
