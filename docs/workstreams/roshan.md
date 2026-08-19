# Worklog — Roshan

Role: intelligence, sources, data, FTA. Writes data into the system through the shared API. No UI.
Ordered backlog; take the top **Next up** item unless client priorities say otherwise, and note
why if you skip one. Move finished items to **Done**.

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

**Lane note, 28 Jul 2026 — closed out 6 Aug.** #117/#118/#120/#121/#122/#130 (persistence adapter,
audit service, run + candidate endpoints, REQ-I-05 acceptance criteria, restart/rehydration test)
were assigned to me as a **one-off delegation to balance Bhanu's workload, not a lane transfer** —
confirmed with him directly. All six are now done or in final review (below); `/services/api`,
`/database` and `/schemas` revert to being his lane as of #130 merging — nothing further under
those paths gets picked up without asking him first.

- #117, #118, #122: closed (PRs #163, #154, and #118's own PR).
- #120 (PR #237) and #121 (PR #242): **merged 5 Aug.**
- #130: **PR #248 auto-closed** when `feat/roshan/run-endpoints` was deleted on #237's merge — its
  base branch vanished, not a rejection. Rebuilt clean against current `main` (same commit,
  cherry-picked, re-verified) as **PR #255, CI green, awaiting review.**

**#237's CI anomaly (4+ pushes, zero workflow runs, confirmed via the Actions API not just a stale
`gh pr checks`) never got a root cause** — Bhanu approved and merged it anyway, on the strength of
the local Postgres verification (114 passed) in the PR body. Worth a standup mention in case the
same branch-level fault hits someone else's PR later; not otherwise unresolved.

## In review (opened, awaiting merge)
- [ ] Registers: action-register, watch-lists, exceptions (#209): the controlled launch recorded
  source outcomes, exceptions and carried-forward actions by hand — schema for all three has
  existed since DB schema v0.1 (Bhanu's Workstream A), nothing wrote to it. Built persistence +
  API only, explicitly not `docs/sip/build-plan.md`'s "Registers UI" (Paras's Workstream C) —
  recorded so the lane split stays visible, same pattern as `source_checks.py`/
  `comms_persistence.py` this week. `exceptions` is append-only per SIP-050's own rule
  (`record()`/`correct()` both insert, `correct()` never touches the row it corrects —
  `correction_ref` carries the original id forward, same shape as `decision_records.
  supersedes_id`); `action_register`/`watch_lists` update in place since they're operational
  trackers, not evidence — `closed_at` set only on exactly `Closed`, verified by mutating that
  check and confirming the test written for it fails. 842 passed against a real local Postgres,
  ruff clean, `EXPECTED_ROLES` map caught all 12 new routes on first run as designed, `pnpm -r
  lint`/`typecheck` clean, OpenAPI + TS clients regenerated, `schemas/api-contract.md` updated.
- [ ] Approved facts library (#188, PR #321): `approved_facts` table + `FactRepository`
  (draft/approve/archive, self-approval refused at both the app layer and a schema CHECK
  constraint) + `/api/facts` (Analyst drafts, Reviewer/SIP Owner approves - same split as
  `candidates/verify`). Corrections chain via `supersedes_id` rather than overwriting, same
  pattern `decision_records` uses. 20 new tests, 803 total passing, 9/9 CI green, MERGEABLE.
  Branched fresh off `main` rather than stacked on the existing registers branch, since #319 (also
  mine, also awaiting review) is a separate PR and mixing new scope into it mid-review would have
  changed what its reviewer sees.
- [ ] Backend restart/rehydration integration test (#130, PR #255): kills a real `uvicorn`
  subprocess mid-run and starts a fresh one on the same port, proving a run's state survives an
  actual process restart, not just a fresh request. CI green (151 passed against a real local
  Postgres running the actual merged `main` — both #120's and #121's routers, plus Bhanu's
  hardening middleware).
- [ ] Dashboard generated-types drift (#271, PR #274): found while chasing an unrelated `frontend`
  CI failure on #273 — `apps/dashboard/ui/src/api/schema.ts` was a generation behind because #268
  branched before #261 added `POST /api/comms/draft`, so `pnpm run codegen`'s drift check fails on
  every PR that touches Python, including mine. Someone had already filed #271 with the exact
  diagnosis and fix; ran `pnpm run codegen` on current `main` and committed just the one stale
  file — no source change. `pnpm -r lint`/`typecheck` clean across all five UI workspaces, all 9
  CI checks green. Once this merges, #273's `frontend` check clears on rebase too.
- [ ] Central tariff database for the Explainer (#185, PR #273): `TariffOutcome` carries
  direction/current/commencement/staged/final tariff + implementation period, sourced from the
  NIA's Key Tariff Outcomes table. Second commit wires those fields into `ExplainerAnswer` itself
  (`_to_answer()`) — the first commit only added them to the corpus, so a member query still
  returned free-text `treatment` only; #185's own wording is the Explainer must answer a tariff
  question "from" the data, not have it filed away unused. `apps/fta` + `apps/fta/tests` (37
  passed) and `docs/fta-source-corpus.md`'s member-facing-mapping section updated to match. The
  `frontend` check that was red here was the #271 generated-types drift, not this diff; #274 fixed
  it on `main`, so the check clears on this rebase (13 Aug 2026).

## Next up
- SHARED-OK: SIP-050 relevance/signal/confidence scoring moved to Bhanu's worklog — it runs
  through the model gateway he owns. `assessment.py` stays the validation/carry layer here.
- [ ] Comms Assistant service side (`apps/comms`): draft-generation flow with the named-reviewer
  gate, per [docs/modules/comms-assistant.md](../modules/comms-assistant.md). **Unblocked as of
  12 Aug:** the Executive Sponsor approved the redaction policy on 9 August, and it is committed at
  `config/redaction-policy.json` (`docs/redaction-policy.md`). The service side can now be built.
  The gateway still refuses every call wherever `REDACTION_POLICY_PATH` is unset, which is the
  intended default, so a live call needs that set in the environment as well. Non-negotiable per
  `comms-assistant.md`'s "drafts only, adversarially tested" promise: the named-reviewer gate is
  not optional. Boundary refusal has since landed too, so every model call declares a
  `PromptSource` and a prompt built from member records must go through `minimise()` and declare
  `MINIMISED_RECORD`. The brief itself is `STAFF_AUTHORED`, which is a declaration rather than a
  guarantee the text is clean, so do not paste member details into one.
- [ ] End-to-end pipeline run once org-repo secrets land (Bhanu's item): collector → capture →
  assessment live against the SIP-184 SOP; fix what breaks; record the run. (#55's own detailed
  progress log lives on `feat/roshan/sip-dry-run`/PR #264 — not duplicated here until it merges,
  to avoid two branches disagreeing about the same narrative.)
- [ ] Collection-engine reliability (#208, via `daily-india-nz-news-agent`'s own PR flow). 4-day
  plan, all four days now built: Day 1 — test harness, `daily-india-nz-news-agent#13` (49
  characterization tests; a real `ModuleNotFoundError` under plain `pytest` found and fixed via
  `tests/conftest.py`, reverified against CI's exact invocation). Days 2-4 — `#14`, stacked on
  `#13`'s branch (not `main`) so review can start without waiting on `#13` to merge: source
  freshness classification (`ok`/`no_recent`/`empty`/`error`, distinguishing a quiet news day from
  a dead feed — RSS and the three GDELT-backed sources need opposite rules since GDELT applies its
  time window server-side); timeout+retry+entry-shape recovery on `fetch_rss_news` (which had
  **no timeout at all** before this, unlike GDELT's existing `timeout=45`) and retry on
  `gdelt_query`; a regression test locking `SIP_AUTOMATED_DISTRIBUTION_ENABLED`'s default-off and
  exact-string comparison. 12 commits, 121 tests, all mutation-tested (each real defect verified
  by deliberately reintroducing it and confirming the test suite caught it) — including two bugs
  caught during development itself: the coverage-qualified no-signal line first claimed "all
  sources answered" with zero outcomes recorded, and `retry_transient`'s default `sleep=time.sleep`
  bound the real function at import time so a test patching `agent.time.sleep` never reached it,
  hanging the suite on real sleeps until found. `#14` is `MERGEABLE`, 5/5 CI green. Left open by
  design rather than solved unilaterally: cross-run freshness-counter persistence, written up with
  real tradeoffs in `docs/source-freshness.md` for the team to decide.
- [ ] Bump the CI ruff pin to 0.16.0 (#31): the collector/FTA findings are fixed and merged (PR
  #152), but the pin itself is still 0.15.22 pending `apps/sip/core`, `scripts/board.py` and
  `services/api` (Bhanu's lane) going clean under 0.16.0 too.

See Blocked / decisions needed for what's still open before any of this runs live (secrets,
INZBC sector/disclaimer sign-off).

## Done
- [x] Backend restart/rehydration integration test (#130, PR #255, merged 7 Aug 2026): kills a real
  `uvicorn` subprocess mid-run and starts a fresh one on the same port, proving a run's state
  survives an actual process restart, not just a fresh request. 151 passed against a real local
  Postgres running the merged `main` — both #120's and #121's routers, plus Bhanu's hardening
  middleware.
- [x] Dashboard generated-types drift (#271, PR #274, merged 12 Aug 2026): found while chasing an
  unrelated `frontend` CI failure on #273 — `apps/dashboard/ui/src/api/schema.ts` was a generation
  behind because #268 branched before #261 added `POST /api/comms/draft`, so `pnpm run codegen`'s
  drift check failed on every PR touching Python. #271 already had the exact diagnosis; ran
  `pnpm run codegen` on current `main` and committed just the one stale file — no source change.
- [x] FTA Explainer retrieval upgrade (#54): `answer_query` now ranks confirmed matches by
  weighted keyword relevance instead of returning an unordered keyword-overlap set. Self-contained
  TF-IDF-style scorer (`_relevance_score`) — no vector service, no new dependency: topic-keyword
  matches score higher than sector-keyword matches, and both are weighted by inverse document
  frequency across confirmed entries, so a common sector word like "agriculture" contributes less
  than a term unique to one or two entries. Ties (e.g. plain "dairy" scoring all four Dairy
  entries equally) break on entry id for a deterministic, repeatable order. Match set is
  unchanged — ranking only orders, an entry with zero shared keywords still scores 0 and is
  excluded, so every existing guarantee (no answer without Tier-1 citation, unconfirmed entries
  suppressed, `[]`/escalate on no match) holds exactly as before. Caught my own test-design bug
  before committing: the first version of the ranking-order test used a query whose correct order
  happened to match `CORPUS`'s insertion order regardless of whether ranking ran at all, so
  disabling ranking entirely still passed it. Replaced with a query ("peptones dairy") where
  ranked and insertion order genuinely differ, confirmed disabling ranking now fails it,
  restored. The neighbouring tiebreak test had the same flaw and was not caught: it compared
  two calls of a pure function, which agree whatever the sort key is, so deleting `entry.id`
  from it left the file passing. Fixed in review by swapping in a corpus built in reverse id
  order, where insertion order and id order genuinely disagree.
- [x] Transactional audit service (#118). `services/api/audit.py` — `record_audit(conn, ...)` writes
  `old_value`/`new_value`/`reason`/`approval_ref` into `audit_log` on the **caller's** open
  connection and never commits, so the audit row shares the mutation's transaction: they commit
  together or not at all. Wired into `persistence.apply_transition`, which now takes `actor_id` +
  `reason` (+ optional `approval_ref`) and records the transition before its single commit — audited
  only when the CAS actually lands, never on a lost race. Immutable **at the database**, not by
  convention: an `audit_log_append_only` trigger reusing the decision tables' existing
  `reject_evidence_change()` refuses UPDATE/DELETE from any role, and the app login role is granted
  INSERT/SELECT only (`database/audit_role.sql`, kept out of `schema.sql` because CI applies the
  schema with no app role existing). Tests (`test_audit.py`, live-Postgres, skip without
  `DATABASE_URL` like #117): trigger refuses UPDATE/DELETE (55000); the INSERT/SELECT-only role is
  refused at the privilege layer (42501, before the trigger); `record_audit` leaves the transaction
  boundary to the caller (a rollback discards it); `apply_transition` writes a matching row; and a
  forced audit-write failure rolls back the state change with it. Verified both new controls bite:
  dropped the trigger → immutability tests fail; committed before the audit write → the atomicity
  test fails; restored. Also a text-level guard in `test_schema_decisions.py` so trigger removal
  fails CI even on the no-DB path. Ran against a real Postgres 16: 256 passed, 98.11% coverage.
- [x] Persistence adapter with concurrency control (#117, closed via PR #163). Optimistic
  concurrency on `runs.version` (compare-and-swap), proven by a real two-thread race against
  Postgres; `apply_transition` also refuses an illegal state jump. Foundational — #120/#121 write
  through it. Now also writes the transition's audit row (#118).
- [x] Pipeline integration test suite wired into CI (#56, closed via PR #151). `FakeSipApi` holds
  state across calls to catch regressions at the seam between modules: capture → cross-run dedupe,
  the verification gate end-to-end, and the mandatory-source Critical stop against the real
  112-source register. Verified it catches a regression before merging.
- [x] Ruff 0.16.0 findings in my lane fixed (#31): `apps/fta` and `apps/sip/collector` are clean
  under 0.16.0. Auto-fixed the mechanical ones (`UP035` typing.Iterable → collections.abc,
  `UP017` datetime.UTC alias, `I001` import sort, `FLY002` f-string). The one real finding,
  `DTZ007` on `mapping.py`'s GDELT `strptime` fallback, got an actual decision rather than a lint
  appeasement: on Python 3.11+ `fromisoformat` already parses the `...Z`-suffixed GDELT format
  directly (aware, UTC), so only the no-separator compact format ever reaches the `strptime`
  loop in practice; GDELT's API docs state every `seendate` is UTC, so that fallback now attaches
  `UTC` explicitly instead of returning an ambiguous naive datetime. Updated the one test whose
  expected output changed as a result. **Not done: bumping the CI pin.** The issue assumed only
  3 findings existed tree-wide; `apps/sip/core`, `scripts/board.py` and `services/api` now have 7
  more (subclass slots ordering, `datetime.UTC` alias, blind `except Exception`, `subprocess.run`
  without `check`) — all outside my lane per the PROJECT-RULES.md rule that `/services/api` changes go
  through Bhanu. Bumping the pin now would break CI tree-wide on code I don't own; pin stays at
  `0.15.22` until those are fixed too. Raising at standup rather than guessing at someone else's
  code.
- [x] Pipeline integration test suite (#56). New
  `apps/sip/collector/tests/test_pipeline_integration.py`: `FakeSipApi`, an in-memory stand-in
  that actually stores candidates/source-checks across calls (unlike the per-module unit tests'
  stubs, which only record what they were asked to do) — the point is to catch a regression at
  the seam between modules, not just within one. Covers capture → cross-run dedupe (by url),
  malformed-article resilience, the verification gate end-to-end through
  `apply_candidate_assessment` (blocks unverified High, allows verified High, blocks a
  verification downgrade on an already-Critical candidate), and the mandatory-source Critical
  stop against the real 112-source v1.0 register (not a handful of fixture sources — a suite that
  only exercises 2-3 sources wouldn't catch a gate that only works for small inputs), both the
  gap-reporting and full-coverage paths. Verified the suite actually catches a regression before
  committing: temporarily disabled the verification-gate call in `assessment.py`, confirmed the
  gate test failed, restored it. "Wired into CI" needed no workflow change — `pyproject.toml`'s
  `testpaths` already runs everything under `apps`/`services`, so this suite runs on every PR
  Bhanu's existing `ci.yml` `python` job already gates on.
- [x] Config nit from PR #17: moved `No Material New Signal` out of `source_outcome_extras` in
  `docs/sip/SIP_Reference_Config.json` — SIP-185 line 59 is explicit it's the day-level run
  conclusion (SIP-184 §9), not a per-source outcome code, so the config disagreed with the doc it
  mirrors. No code referenced the removed value.
- [x] REQ-I-05 acceptance criteria (#122, closed): the only requirement in `docs/requirements.md`
  with none, so there was no definition of done for the end-to-end pipeline run (#55). Scoped to
  SIP-184 §1-7; each criterion distinguishes "tested against fakes" from "proven against a live
  run" to match the requirement's own Blocked status. Merged via PR #154.
- [x] Client + lookup layer for `GET /api/source-library`, implemented locally ahead of the
  endpoint (refs #52 — not closed; the endpoint itself isn't deployed yet, see below). New
  `apps/sip/collector/source_lookup.py`: `build_source_lookups()` splits one
  `SipPipelineClient.get_source_library()` response into `SourceNameLookup` (display name → db id,
  for `mapping`/`ingest`) and `SourceIdLookup` (SIP-185 code → db id, for
  `record_source_outcome`) — two distinct dataclasses, not interchangeable dicts, so a caller
  can't pass a name-keyed lookup (or any non-`SourceIdLookup`, including a plain dict) where the
  id-keyed coverage gate expects one; `record_source_outcome` checks positively for
  `SourceIdLookup` and raises `TypeError` on anything else. A name shared by more than one record
  (two exist in the v1.0 register — "Ministry of Defence", "Ministry of Education", once per
  jurisdiction) is dropped from the name lookup rather than resolving to whichever record was
  seen last (caught in Bhanu's PR #131 review — the initial version let the second record
  silently overwrite the first). Added `SipPipelineClient.get_source_library()`. Candidate capture
  still degrades to `source_id=None` on an unmatched name (nullable column); source-check
  recording still raises `SourceIdUnresolved` on a miss (NOT NULL column) — unchanged from before.
  **Not done here:** the `/api/source-library` endpoint itself — `services/api` only serves
  `/api/fta/query` and `/health` today, so `get_source_library()` returns 404 until that server
  work lands (separate PR, per ADR-0004's sequencing). Nothing in this PR is reachable end-to-end
  yet; it's the client/lookup layer landing ahead of the server, the established pattern here.
  **Second review round** (deeper pass, five more findings — two fixed as required, three fixed
  as cheap hardening rather than deferred): (1) name dedup compared raw names while
  `mapping.map_article` looks up a stripped one, so a whitespace-only variant defeated the
  round-one fix — `SourceNameLookup` now strips both stored keys and lookup arguments; (2) the
  `isinstance(x, SourceIdLookup)` guard let a subclass overriding `get()` walk straight through —
  switched to an exact `type(x) is SourceIdLookup` check, the same fix already applied once to the
  orchestrator's human-decision gate; (3) a duplicate `sip185_code` now raises
  `DuplicateSip185Code` instead of silently keeping the last row (the schema declares it unique,
  so a duplicate means malformed data, not something to paper over); (4) both lookup dataclasses
  now copy their input dict in `__post_init__`, since `frozen=True` only stops the field being
  rebound, not its contents being mutated through a caller's reference; (5) the null-code test now
  asserts `id_lookup.get(None) is None` directly instead of a proxy assertion that wouldn't have
  caught its own regression.
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

## SHARED-OK — work taken in this lane by Bhanu

Recorded here, not only in the PR descriptions, per the lane rule in
[docs/workstreams/README.md](README.md). Raised at the next stand-up; object if any of it should
come back.

- **`apps/fta/explainer.py` — `NoMatch` / `no_match()`** (PR #83, 26 Jul 2026). Builds the Action
  Required state a caller renders when `answer_query` returns `[]`. Deliberately not shaped like
  `ExplainerAnswer` so a renderer cannot present escalation as a sourced finding. `answer_query`
  itself is unchanged. Taken to unblock the API endpoint on the critical path.
- **`apps/fta/corpus.py` — stable `id` on every entry** (PR #89, 26 Jul 2026). `FTA-001`-style
  codes following the SIP-185 convention. The UI was keying React lists and ARIA ids off `topic`,
  which is prose containing spaces, so `aria-labelledby` silently failed. Ids are assigned once
  and must never be renumbered or reused.
- **Still yours:** FTA retrieval ranking, corpus content and sourcing, `assessment.py`, the
  collector and pipeline. Nothing in this lane's judgement calls was changed — only identifiers
  and an additive helper.

## Blocked / decisions needed
- FTA sectors in scope + disclaimer wording (INZBC to confirm).
- Collection-engine secrets in the org repo (needs the values) — blocks running the collector
  end-to-end even though the mapping is written. (Bhanu owns org-repo secrets setup + rotation —
  on his worklog.)

## Studio 5 PDR — what I need for a pass (competency-based, all 6 objectives required)

Per `IA728001 Studio 5 Performance and Development Review` (final PDR meeting, Week 9). Not
project scope — my own pass-tracking. Update as evidence accumulates; bring this + screenshots to
the practice PDR (Week 5) and final PDR.

| Obj | Requirement | Status | Evidence I have | Still need |
|---|---|---|---|---|
| 1.1 | Capture requirements via a methodology/tool | 🟢 Done | ADR-0001, SIP-050/184/185 specs, `schemas/api-contract.md`/`state-machine.md` followed exactly for #120/#121's endpoint shapes | — |
| 1.2 | Contribute meaningfully — **steady and regular**, not just volume | 🟢 | Merged/opened PRs now span **eight distinct days**: 22 Jul, 28-31 Jul, and 3-5 Aug (#237/#242/#248 this week alone) | Keep the cadence into the rest of the block — eight days across three weeks is real, no longer the single-day risk it was |
| 2.1 | Independent research, justified decisions | 🟢 Done | MFAT source verification, FTA corpus confirmed/unconfirmed flags, ADR-0005 §7 read to confirm candidate commands don't need `decision_records`, mutation-tested every new gate/test before committing | — |
| 3.1 | Team communication | 🟡 | Standup log `2026-07-20-week.md`, client meeting `2026-07-22-inzbc.md` | Still no standup/client-meeting record past 22 Jul — log this week's before the PDR |
| 3.2 | Industry-standard PM tools, used professionally | 🟢 Done | Every PR closes/refs an issue; issue labels kept current (`stage:in-progress` on #120/#121/#130 as PRs opened); GitHub Projects board linked automatically via PR body | Board *Status* field stuck on "Todo" for #120/#121 — account lacks write permission on the board itself, flagged for Bhanu/admin, not something I can self-fix |
| 3.3 | Documentation (technical + reflective) | 🟢 Done | Module docstrings, this worklog, PR evidence blocks, `apps/sip/collector/README.md` | Reflective report still owed before the PDR — separate from technical docs |

**This week's remaining risk is just 3.1** — everything else has real evidence now. #237's CI
anomaly resolved itself (Bhanu merged on the strength of local verification) and isn't a live
concern anymore.

**Weekly hours target: 22-24h**, not just the assignment's 20h floor — the buffer absorbs a thin
day (blocked review, a meeting running long) without dropping under the pass threshold. Tracked in
`Studio5-Timesheet-RoshanAryal.xlsx`, one tab per week.

## Definition of done
A run opens, sources are recorded with outcomes, candidates captured and verified, and written to
the DB through the API. FTA answers cite Tier-1 sources with effective dates. No control-plane writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
