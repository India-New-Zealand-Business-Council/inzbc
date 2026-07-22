# Worklog — Roshan

Role: intelligence, sources, data, FTA. Writes data into the system through the shared API. No UI.
Ordered backlog; take the top **Next up** item. Move finished items to **Done**.

## Lanes (my paths)
```
/apps/fta/**
/apps/comms/**        (service side; Paras owns the UI side)
/apps/sip/pipeline/**
/apps/sip/collector/** (integration with the daily-india-nz-news-agent repo)
```
Cross-repo: the collection engine lives in `daily-india-nz-news-agent`. Improve it there via its
own PR flow; this lane is the integration that pulls its output into SIP.

## Modules I own (see [docs/modules](../modules/README.md))
[SIP pipeline](../sip/) (collection, sources, candidates, verification) +
[FTA Implementation Centre](../modules/fta-centre.md) + Explainer service +
[Communications Assistant](../modules/comms-assistant.md) service side (Paras owns its UI).

## Depends on (Bhanu's contracts)
DB schema, API contract, auth. Build against them; don't write to control-plane tables.

## Next up
Nothing queued. See Blocked / decisions needed for what's open before any of this runs live, and
for the relevance/signal/confidence scoring decision that needs Bhanu, not more Roshan-side code.

## Done
- [x] Wire the collection-engine output into SIP candidate capture via the API (run to
  candidates). `apps/sip/collector/mapping.py` + `ingest.py`, mapped against the real
  `daily-india-nz-news-agent` `clean_articles()` output. Raw capture only (SIP-184 step 5); no
  live run yet — see blockers below.
- [x] Source register + per-source outcomes (SIP-185), fallback attempts recorded.
  `apps/sip/collector/source_register.py`: `MANDATORY_SOURCES` mirrors SIP-185's worklist,
  `missing_mandatory_outcomes()` enforces the "blank mandatory outcome is a Critical stop" rule
  client-side, `record_source_outcome()` builds a `SourceCheck` and folds the fallback-attempt
  trail into `notes`. `source_checks.source_id` is NOT NULL in the DB, so unlike candidate
  capture this cannot degrade to an unresolved id — it raises `SourceIdUnresolved` instead.
- [x] Candidate capture: all fields (relevance, signal, confidence, verification, duplicate
  status, routing). Tightened `Candidate.nz/india/member_relevance` to actually enforce 0..5
  (ADR-0001 commits to Pydantic validation at the trust boundary; the comment said 0..5 but
  nothing enforced it). Added `apps/sip/collector/assessment.py`
  (`CandidateAssessment`/`apply_candidate_assessment`, the PATCH path for scoring/verification/
  routing) and `dedupe.py` (`find_duplicate_of`, cross-run duplicate matching by url/headline).
  Does not compute relevance/signal/confidence values itself — see blockers.
- [x] Verification/citation controls: High/Critical claims need an official/high-confidence
  source; block unverified Critical. `apps/sip/collector/verification.py`:
  `enforce_verification_gate()` refuses a High/Critical assessment when verification is
  Unverified, Rejected, or unknown (unknown treated as unverified, fail closed). Wired into
  `apply_candidate_assessment()` ahead of every PATCH.
- [x] FTA source corpus (Tier 1 official first) + freshness/effective-date tracking.
  `apps/fta/corpus.py` mirrors `docs/fta-source-corpus.md`'s Tier 1/2 sources and verified
  tariff outcomes as structured `TariffOutcome` entries (each with its own `confirmed` flag and
  citation, so the still-unconfirmed ~70% tariff-line figure stays marked unconfirmed rather than
  omitted or asserted). `stale_entries()` gives freshness tracking by `verified_at` age; it takes
  `review_after_days` with no default since INZBC hasn't set a review cadence — see blockers.
- [x] FTA Explainer service: sector query to sourced answer with citation + effective date +
  next step. `apps/fta/explainer.py`: `answer_query()` matches a query against the corpus by
  shared keyword (no model call) and returns treatment + status line + jurisdiction + citation +
  verified date + next step + disclaimer per match; `[]` on no match routes to INZBC rather than
  guessing. Disclaimer field is a literal `[[INZBC-approved disclaimer wording pending]]`
  placeholder, not authored copy — see blockers.
- [x] Addressed Bhanu's PR #23 review (CHANGES_REQUESTED). Blocking: `verification.py` switched
  to an allowlist (only Verified/Partially Verified pass for High/Critical — `Not Required` now
  correctly fails closed too, per SIP-050 sections 14/27); `explainer.py` now suppresses
  `confirmed=False` corpus entries entirely from member answers (escalates to INZBC instead of
  returning the unconfirmed ~70% tariff-line figure with a caveat). Notes addressed:
  `apply_candidate_assessment()` takes `current_signal` (mirroring `current_verification`) so a
  verification downgrade on an already-High/Critical candidate is caught; `mapping.py`'s
  `in_coverage_window=True` simplification documented explicitly (agent's rolling filter vs.
  SIP-184's fixed 07:00 NZT window); `ingest_articles()` now maps each article inside its own
  try/except so one malformed article no longer aborts the whole batch.
- [x] Wired the now-live `GET /api/source-library` (PR #25) into the collector.
  `apps/sip/pipeline/client.py`'s `list_source_library()` + `models.py`'s `SourceLibraryEntry`
  (column parity checked against `database/schema.sql`, same guard style as the enum test), and
  `apps/sip/collector/source_lookup.py`'s `fetch_source_lookup()`/`build_source_lookup()` build
  the name → id map that `map_article`/`ingest_articles`/`record_source_outcome` already accepted
  as `source_lookup`. Only `active` source_library rows resolve.
- [x] Read SIP-050 in full (PR #26) to scope the "build real scoring" follow-up. Only section 7
  (Coverage Window and Freshness) is mechanically computable from a timestamp; sections 11-13
  (NZ/member relevance tests, signal strength, source confidence) are qualitative judgment calls
  for an analyst or a model-assisted recommendation, not something a keyword heuristic here could
  compute honestly — see the decision recorded in Blocked / decisions needed. Implemented the
  mechanical part: `apps/sip/collector/freshness.py`'s `compute_in_coverage_window()` (inclusive
  start / exclusive end, `None` when a timestamp is missing/unparseable/timezone-naive rather
  than guessing) now replaces `mapping.py`'s hardcoded `in_coverage_window=True`; `map_article`/
  `map_articles`/`ingest_articles` take the run's `coverage_start_utc`/`coverage_end_utc`.

## Blocked / decisions needed
- FTA sectors in scope + disclaimer wording (INZBC to confirm).
- Collection-engine secrets in the org repo (needs the values) — blocks running the collector
  end-to-end even though the mapping is written.
- Relevance/signal/confidence scoring (SIP-050 sections 11-13) needs a model-calling service —
  `docs/sip/README.md`'s non-negotiables put "scoring, model calls" server-side only, which is
  `services/api` (Bhanu's lane), not `apps/sip/collector`. This isn't a Roshan-side coding task
  until that service/decision exists; `assessment.py` stays a validated pass-through until then.

## Definition of done
A run opens, sources are recorded with outcomes, candidates captured and verified, and written to
the DB through the API. FTA answers cite Tier-1 sources with effective dates. No control-plane writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
