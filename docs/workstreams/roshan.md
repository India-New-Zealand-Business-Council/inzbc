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

## Next up
- SHARED-OK: SIP-050 relevance/signal/confidence scoring moved to Bhanu's worklog — it runs
  through the model gateway he owns. `assessment.py` stays the validation/carry layer here.
- [ ] Comms Assistant service side (`apps/comms`): draft-generation flow with the named-reviewer
  gate, per [docs/modules/comms-assistant.md](../modules/comms-assistant.md); model calls route
  through Bhanu's gateway once it lands.
- [ ] FTA Explainer retrieval upgrade: replace `explainer.py`'s keyword matching with ranked
  retrieval over the corpus — still no answer without a Tier-1 citation; `[]`/escalate on
  low-confidence matches stays.
- [ ] End-to-end pipeline run once org-repo secrets land (Bhanu's item): collector → capture →
  assessment live against the SIP-184 SOP; fix what breaks; record the run.
- [ ] Pipeline integration test suite wired into CI: verification gate, dedupe, mandatory-source
  stops, malformed-article handling — the fail-closed behaviour currently has no automated tests.
- [ ] Collection-engine improvements in `daily-india-nz-news-agent` (via its own PR flow).

See Blocked / decisions needed for what's still open before any of this runs live (secrets,
INZBC sector/disclaimer sign-off).

## Done
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
  without `check`) — all outside my lane per the CLAUDE.md rule that `/services/api` changes go
  through Bhanu. Bumping the pin now would break CI tree-wide on code I don't own; pin stays at
  `0.15.22` until those are fixed too. Raising at standup rather than guessing at someone else's
  code.
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
| 1.1 | Capture requirements via a methodology/tool | 🟢 | ADR-0001, SIP-050/184/185 specs, GitHub issues #52-56 | — |
| 1.2 | Contribute meaningfully — **steady and regular**, not just volume | 🔴 | 25 commits, 5 merged PRs (#14,#15,#17,#19,#23) — but **all dated 22 Jul**, one day | Commits spread across *multiple distinct days* this block. One heavy day reads as a cram, not sustained contribution — this is the single biggest pass risk. |
| 2.1 | Independent research, justified decisions | 🟢 | MFAT source verification (PR #14/#15), FTA corpus confirmed/unconfirmed flags, ADR-0001 rationale | Keep citing sources in PR descriptions as I go |
| 3.1 | Team communication | 🟡 | none gathered yet | Screenshot/log standup (17:00 daily) and Wednesday client meeting attendance; keep PR review comment threads as evidence |
| 3.2 | Industry-standard PM tools, used professionally | 🟡 | GitHub issues + org project board exist | Actually reference the board/issues in commits and PRs (e.g. "closes #52"), not just have them exist |
| 3.3 | Documentation (technical + reflective) | 🟢 | Module docstrings, this worklog, PR evidence blocks, `apps/sip/collector/README.md` | Add a reflective report before the PDR — the marking criteria explicitly ask for one, separate from technical docs |

**Action for this week:** don't batch commits into one sitting even when the code is ready sooner —
land one focused PR per day against the open issues (#52 done; #31, #54, #56 next), so the git
history itself is 3.1/1.2 evidence instead of a liability.

**Weekly hours target: 22-24h**, not just the assignment's 20h floor — the buffer absorbs a thin
day (blocked review, a meeting running long) without dropping under the pass threshold. Tracked in
`Studio5-Timesheet-RoshanAryal.xlsx`, one tab per week.

## Definition of done
A run opens, sources are recorded with outcomes, candidates captured and verified, and written to
the DB through the API. FTA answers cite Tier-1 sources with effective dates. No control-plane writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
