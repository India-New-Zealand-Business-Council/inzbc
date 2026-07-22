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
- [ ] FTA source corpus (Tier 1 official first) + freshness/effective-date tracking.
- [ ] FTA Explainer service: sector query to sourced answer with citation + effective date + next step.

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

## Blocked / decisions needed
- FTA sectors in scope + disclaimer wording (INZBC to confirm).
- Collection-engine secrets in the org repo (needs the values) — blocks running the collector
  end-to-end even though the mapping is written.
- `source_library` name lookup: no endpoint in `schemas/api-contract.md` to resolve a source
  name to its DB id. Candidate capture degrades to `source_id=None` without it (the column is
  nullable); source-check recording cannot — `record_source_outcome()` raises rather than
  writing an invalid row. Needs a contract change from Bhanu (`GET /api/source-library` or
  similar) before source outcomes can actually be submitted.
- SIP-050 (approved scoring/prompt framework) isn't in this repo yet (`docs/sip/README.md` TODO)
  — blocks building actual relevance/signal/confidence scoring logic; `assessment.py` currently
  only carries analyst/model-supplied values through with validation.

## Definition of done
A run opens, sources are recorded with outcomes, candidates captured and verified, and written to
the DB through the API. FTA answers cite Tier-1 sources with effective dates. No control-plane writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
