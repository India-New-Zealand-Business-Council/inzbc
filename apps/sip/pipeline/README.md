# apps/sip/pipeline — intelligence pipeline (data in)

Owner: Roshan. Implements the "Pipeline (Roshan) — data in" section of
`schemas/api-contract.md`: run control, source-check recording, candidate capture. Writes to the
DB only through Bhanu's API — never touches `database/schema.sql` directly.

- `client.py` — REST client wrapping every pipeline endpoint in the API contract, including
  `list_source_library()` (`GET /api/source-library`, added in PR #25).
- `models.py` — request/response shapes mirroring `database/schema.sql`'s `runs`, `source_checks`,
  `candidates`, and `source_library` tables, including the shared enums.
- `tests/` — local checks that don't require a live server: enum parity and
  `SourceLibraryEntry` column parity against the schema.

No live API exists yet (`services/api` is still a stub), so nothing here can be run end-to-end.
This module is ready to point at a real base URL once Bhanu's server exists.

See `docs/workstreams/roshan.md` for the backlog this serves, and `apps/sip/collector/README.md`
for what's still blocking the collector side.
