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
- [ ] Wire the now-live `GET /api/source-library` (PR #25) into `source_lookup` so candidate and
  source-check writes resolve real ids instead of degrading to `source_id=None`/raising
  `SourceIdUnresolved`. Flagged as a follow-up in Bhanu's PR #23 review, not done in that PR.
- SHARED-OK: SIP-050 relevance/signal/confidence scoring moved to Bhanu's worklog — it runs
  through the model gateway he owns. `assessment.py` stays the validation/carry layer here.

See Blocked / decisions needed for what's still open before any of this runs live (secrets,
INZBC sector/disclaimer sign-off).

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
- [x] Addressed Bhanu's second PR #23 review round (CHANGES_REQUESTED again, closer read of the
  first fixes). `apply_candidate_assessment()` now refuses (`MissingCurrentSignalError`) a patch
  that downgrades verification away from Verified/Partially Verified without also setting
  `signal`, when `current_signal` wasn't supplied either — previously that case silently fell
  through to `effective_signal=None`, failing the gate open exactly when a candidate is already
  High/Critical. `parse_published_at()` now checks `isinstance(raw, str)` instead of calling
  `.strip()` unconditionally, so a non-string `published` value (untrusted agent output) is
  treated as unparseable instead of raising `AttributeError` past `ingest_articles()`'s catch
  list. `explainer.py` stopwords jurisdiction terms (india/indian/nz/new/zealand) so a query
  like "education in India" can't spuriously match on the jurisdiction word alone and returns
  `[]` (escalate to INZBC) instead of a wrong cross-sector entry. Also: `record_source_outcome`'s
  `fallback_used` now checks whether the final attempt differs from `FALLBACK_SEQUENCE[0]`
  rather than `len(fallback_attempts) > 1`, so a single non-direct attempt is correctly flagged
  as a fallback; stale "no lookup endpoint yet" comments in `source_register.py`/`mapping.py`/
  the collector README updated to reflect that `GET /api/source-library` exists (PR #25),
  wiring it in is just tracked separately, not done in this PR.

## Blocked / decisions needed
- FTA sectors in scope + disclaimer wording (INZBC to confirm).
- Collection-engine secrets in the org repo (needs the values) — blocks running the collector
  end-to-end even though the mapping is written. (Bhanu owns org-repo secrets setup + rotation —
  on his worklog.)

## Definition of done
A run opens, sources are recorded with outcomes, candidates captured and verified, and written to
the DB through the API. FTA answers cite Tier-1 sources with effective dates. No control-plane writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
