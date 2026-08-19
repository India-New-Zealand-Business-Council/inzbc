"""`/api/source-library` (#55): read-only list of `source_library` rows.

`schemas/api-contract.md` documented this route since 22 Jul (#25) but it was never implemented -
`apps/sip/pipeline/client.py`'s `get_source_library()` had nothing to call, and
`apps/sip/collector/source_lookup.build_source_lookups()` could never resolve a source name or
SIP-185 code to a db id, so `source_register.record_source_outcome()` always raised
`SourceIdUnresolved`. Built while unblocking #55's dry run.

Same shape as `services/api/runs.py`: a thin router over a repository, `Depends`-overridden in
tests, `SourceLibraryRepository` proven against a real Postgres in `test_source_library.py` (skips
without `DATABASE_URL`, same convention as `test_persistence.py`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from fastapi import APIRouter, Depends
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict

from services.api.auth import STAFF_READ, Principal
from services.api.session import AUTH_RESPONSES, read_access

router = APIRouter(prefix="/api/source-library", tags=["Source library"], responses=AUTH_RESPONSES)


@dataclass(frozen=True)
class SourceLibraryRow:
    id: str
    sip185_code: str | None
    name: str


class SourceLibraryRepository:
    """Postgres-backed read of `source_library`. No writes here - seeding is
    `scripts/seed_source_library.py`'s job, not this request-scoped repository's.
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def list_sources(self) -> list[SourceLibraryRow]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute("select id, sip185_code, name from source_library").fetchall()
        return [
            SourceLibraryRow(id=str(row["id"]), sip185_code=row["sip185_code"], name=row["name"])
            for row in rows
        ]


def get_source_library_repository() -> SourceLibraryRepository:
    """FastAPI dependency, overridden in tests - same reasoning as `services/api/runs.py`'s
    `get_run_repository`.
    """
    return SourceLibraryRepository()


class SourceLibraryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    sip185_code: str | None
    name: str


@router.get("", response_model=list[SourceLibraryOut])
def list_source_library(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: SourceLibraryRepository = Depends(get_source_library_repository),
) -> list[SourceLibraryOut]:
    return [
        SourceLibraryOut(id=row.id, sip185_code=row.sip185_code, name=row.name)
        for row in repo.list_sources()
    ]
