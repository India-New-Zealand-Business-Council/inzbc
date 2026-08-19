# apps/sip/collector — integration with the collection agent

Owner: Roshan. Maps the `daily-india-nz-news-agent` repo's output onto
`apps/sip/pipeline`'s `Candidate` model, then writes it into an existing run via
`apps/sip/pipeline/client.py`.

- `mapping.py` — `map_article()`/`map_articles()`: turns one of `agent.py`'s `clean_articles()`
  output dicts into a `Candidate` (SIP-184 step 5, raw capture only — no scoring, verification,
  duplicate or routing decisions; those are later SOP steps). Read from the actual agent source
  in `india-new-zealand-business-council/daily-india-nz-news-agent`, not an assumed schema.
  **Known simplification:** `in_coverage_window` is hardcoded `True` rather than computed
  against the run's locked window — see the docstring on `map_article` for why the agent's own
  rolling filter isn't quite the same boundary as SIP-184's fixed 07:00-to-07:00 NZT window.
- `ingest.py` — `ingest_articles()`: maps a batch and POSTs each to `/api/candidates` via
  `SipPipelineClient.create_candidate`, collecting per-item failures instead of aborting the
  batch on the first one. Takes a required `actor_id` — `CaptureCandidateIn`
  (`services/api/candidates.py`) requires it in the body (audit-only, not a `Candidate` field);
  found by running #55's dry run against a live server, not by any test against a fake.
- `source_register.py` — SIP-185's mandatory source worklist (`MANDATORY_SOURCES`), the fallback
  sequence, `missing_mandatory_outcomes()` (client-side check mirroring SIP-184's "blank
  mandatory-source outcome is a Critical stop"), and `record_source_outcome()` to build a
  `SourceCheck` per source, folding a fallback-attempt trail into `notes` since the table has no
  separate attempts column.
- `dedupe.py` — `find_duplicate_of()`: matches a new article against already-captured candidates
  (e.g. from `SipPipelineClient.list_candidates`) by normalized url then normalized headline, for
  setting `duplicate_of` on capture. `clean_articles()` only dedupes within one fetch; this
  covers the same story recurring across runs.
- `assessment.py` — `CandidateAssessment` + `apply_candidate_assessment()`: the SIP-184 step 6-7
  update path (relevance, signal, confidence, verification, duplicate status, routing) applied
  to an already-captured candidate via `PATCH /api/candidates/:id`. Carries values through with
  the same 0-5 relevance validation `Candidate` enforces; does not compute them (see below).
  Runs every assessment through `verification.enforce_verification_gate()` first.
- `verification.py` — `enforce_verification_gate()`: refuses to submit a High/Critical-signal
  assessment whose verification is Unverified, Rejected, or unknown (SIP-184 step 7 and
  `docs/sip/SIP_Reference_Config.json`'s `official_verification_required_for_high/critical`).
  Mirrors the "unverified Critical claim" fail-closed condition from
  `schemas/api-contract.md` client-side, ahead of the server's own enforcement of the same rule.
- `source_lookup.py` — `build_source_lookups()`: splits one `GET /api/source-library` response
  (`SipPipelineClient.get_source_library()`) into `SourceNameLookup` (display name → id, for
  candidate capture) and `SourceIdLookup` (SIP-185 code → id, for source-check recording). A name
  shared by more than one record (two exist in the v1.0 register) is dropped from the name lookup
  rather than resolving to whichever record was seen last; names are compared stripped, matching
  `mapping.map_article`'s stripped lookup, so a whitespace-only variant can't defeat the dedup. A
  duplicate `sip185_code` raises `DuplicateSip185Code` instead of keeping the last row —
  `sip185_code` is declared unique in the schema, so a duplicate can only mean malformed endpoint
  data. Both lookup dataclasses copy their input dict in `__post_init__`, so a caller mutating the
  dict they passed in afterwards can't change an already-built lookup. The two lookup types are
  distinct, not interchangeable dicts, on purpose — `source_library.name` is not unique across
  jurisdictions, so `record_source_outcome` checks `type(x) is SourceIdLookup` exactly (not
  `isinstance`, which a subclass overriding `get()` could walk straight through) and raises
  `TypeError` on anything else.
- `tests/` — local checks against fixture article dicts and a fake client; no live agent or API
  needed.

## Known gap: no scoring framework built yet
`apply_candidate_assessment()` is a validated write path, not a scorer — it does not decide
`nz_relevance`/`india_relevance`/`member_relevance`/`signal`/`confidence`. SIP-050 (the approved
scoring/prompt framework) now exists in the repo, and the SIP non-negotiables put "scoring, model
calls" server-side only — so those values come from an analyst or a future server-side
recommendation, not from this module.

## source_id resolution
`GET /api/source-library` (`schemas/api-contract.md`) returns `id`, `sip185_code`, `name` for every
`source_library` row. `source_lookup.build_source_lookups()` turns one call's response into both
lookups this module needs:
- `map_article`/`map_articles`/`ingest_articles` take an optional `source_name_lookup:
  SourceNameLookup` (article source **name** → id); candidates write with `source_id=None` when a
  name doesn't resolve — `candidates.source_id` is nullable, so this is a degraded-but-valid write.
- `record_source_outcome()` requires a `source_id_lookup: SourceIdLookup` to resolve the SIP-185
  **source id** (e.g. `NZ-OFF-001`) and raises `SourceIdUnresolved` if it doesn't —
  `source_checks.source_id` is **NOT NULL** (`database/schema.sql`), so there is no valid source
  check without one; this can't degrade gracefully the way candidate capture can.

## Live runs (#55) — current state, 8 Aug 2026
Collection-engine secrets are supplied (both `inzbc` and `daily-india-nz-news-agent` have every
secret `docs/sip/README.md` lists). `services/api` is no longer a stub —
`run_dry_run.py` exercises `create_run` → `get_source_library` → `ingest_articles` against a real
Postgres + `services/api`, and running it for real (not just against a fake client) surfaced three
contract bugs no test had ever caught, all now fixed:
- `SipPipelineClient.create_run` sent the whole `Run` model, including server-only fields with
  non-None defaults (`coverage_timezone`) — 422s against `CreateRunIn`'s `extra="forbid"` for
  every real caller. Now sends only the fields `CreateRunIn` accepts.
- `SipPipelineClient.create_candidate` had no way to send `actor_id`, which
  `CaptureCandidateIn` requires — `Candidate` doesn't carry it (it's audit-only, like `runs.py`'s
  `initiated_by`). Now a required second parameter, threaded through `ingest_articles`.
- `GET /api/source-library` didn't exist (`services/api/source_library.py`, #55) and
  `source_library` was never seeded (`scripts/seed_source_library.py`, #55) — both fixed, see
  `docs/workstreams/roshan.md` for the full account.

**Still not wired:** a live `agent.py` fetch. `run_dry_run.py` consumes a fixture file
(`data/dry_run_fixture_articles.json`) rather than pulling real output across repos — that needs a
new PAT secret (infra decision), not something added unilaterally. `POST /api/runs/{id}/source-checks`
(`SipPipelineClient.record_source_check`) also still doesn't exist in `services/api` — found while
building the dry run, not yet fixed, so SIP-184 step 4 (mandatory-source outcome recording) still
can't complete an actual write even though `GET /api/source-library` now resolves the ids it
would need.
