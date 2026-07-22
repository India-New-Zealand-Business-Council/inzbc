# apps/sip/collector — integration with the collection agent

Owner: Roshan. Maps the `daily-india-nz-news-agent` repo's output onto
`apps/sip/pipeline`'s `Candidate` model, then writes it into an existing run via
`apps/sip/pipeline/client.py`.

- `mapping.py` — `map_article()`/`map_articles()`: turns one of `agent.py`'s `clean_articles()`
  output dicts into a `Candidate` (SIP-184 step 5, raw capture only — no scoring, verification,
  duplicate or routing decisions; those are later SOP steps). Read from the actual agent source
  in `india-new-zealand-business-council/daily-india-nz-news-agent`, not an assumed schema. Takes
  the run's `coverage_start_utc`/`coverage_end_utc` and computes `in_coverage_window` against
  them via `freshness.compute_in_coverage_window` (previously hardcoded `True`).
- `freshness.py` — `compute_in_coverage_window()`: SIP-050 section 7's mechanical freshness
  rule (inclusive start, exclusive end against the run's locked window). Only the mechanical
  part of section 7 - "Active Carry-Forward"/"Context"/"Stale" all require judgment about
  whether an older item still has a live trigger, which isn't derivable from a timestamp alone,
  so this module doesn't attempt them.
- `ingest.py` — `ingest_articles()`: maps a batch and POSTs each to `/api/candidates` via
  `SipPipelineClient.create_candidate`, collecting per-item failures instead of aborting the
  batch on the first one.
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
- `source_lookup.py` — `fetch_source_lookup()`/`build_source_lookup()`: calls the now-live
  `GET /api/source-library` (PR #25) and builds the name → id map that `map_article`,
  `map_articles`, `ingest_articles`, and `record_source_outcome()` all take as `source_lookup`.
  Only `active` rows resolve. This is what closes the gap those functions were left with —
  candidate capture no longer has to write `source_id=None`, and source-check recording no
  longer has to raise `SourceIdUnresolved`, as long as the source is actually in the library.
- `tests/` — local checks against fixture article dicts and a fake client; no live agent or API
  needed.

## Deliberately not built: relevance/signal/confidence scoring
`apply_candidate_assessment()` is a validated write path, not a scorer — it does not decide
`nz_relevance`/`india_relevance`/`member_relevance`/`signal`/`confidence`, and that's not
planned to change here. SIP-050 (`docs/sip/launch/SIP-050_master_prompt_v1.1.md`, PR #26) is now
in the repo, and its sections 11-13 define these tests, but they're qualitative judgment calls
("a direct effect on New Zealand trade...", "what changes?", "why it matters") for a human
analyst or a model-assisted recommendation — not something a keyword heuristic in this module
could compute honestly. Faking that judgment in plain Python risks producing wrong signal/
confidence values inside a system that's explicitly fail-closed on exactly those fields
(SIP-050 section 27). `docs/sip/README.md`'s non-negotiables also put "scoring, model calls"
server-side only, which is `services/api` (Bhanu's lane), not this collector module. What SIP-050
section 7 *does* let this module compute mechanically is freshness/coverage-window - see
`freshness.py` above.

## Still blocked
- **Live runs.** Collection-engine secrets (`OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, etc.) aren't
  supplied here, and `services/api` is still a stub — nothing in this module can be exercised
  end-to-end yet, only unit-tested against fixtures. Wire `ingest_articles()` to a real run once
  both exist: create the run via `SipPipelineClient.create_run`, call
  `agent.clean_articles(agent.fetch_news(24))` (or however the agent's `main()` is refactored to
  expose that list), then `ingest_articles(client, run_id, articles)`.
