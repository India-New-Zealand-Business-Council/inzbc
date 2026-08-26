# Seed demo dataset (#338)

`scripts/seed_demo.py` replaces the previous four-candidate demo seed — which did not exist in
this repository (`scripts/seed_demo.py`, `bench_indexes.py`, `demo.cmd` from the original #338
text are not in the history; the issue predates a refactor that removed or never shipped them).
Nothing seeded the SIP tables at all before this script.

## One command

```
psql "$DATABASE_URL" -f database/schema.sql   # once, on an empty database
python -m scripts.seed_demo                    # seeds source_library, then everything else
```

`seed_demo` calls `seed_source_library` itself, so a single command is enough on a fresh database.
Log in locally as any seeded user with `python -m scripts.dev_session --github-login seed-owner`
(also `seed-analyst`, `seed-reviewer`, `seed-reviewer2`, `seed-board`, `seed-auditor`).

## What is seeded

- **6 users**, 7 roles, each user holding 1–2 roles (`@seed.inzbc.test` emails, `seed-<key>` GitHub
  logins).
- **176 `source_library` rows**, all real: the approved SIP-185 v1.0 register
  (`apps/sip/collector/source_register.py`), not invented publications.
- **10 runs** (`RUN-SEED-01` .. `RUN-SEED-10`), spread across 9 distinct `run_state` values —
  Draft, Run Authorised, Coverage Locked, Scanning, Candidate Review, Report Drafted, QA Failed,
  Paused, Distributed, Stopped — each driven there through the real state machine
  (`RunRepository.apply_transition`), not a hand-set column.
- **~80 candidates** across the runs with a deliberately mixed `verification` distribution
  (Verified, Partially Verified, Unverified, Rejected all present) and `signal` distribution (Low
  through Critical), captured/scored/verified through `CandidateRepository` in the order its own
  verification gate requires (a High/Critical signal is only ever set once a candidate is already
  Verified/Partially Verified).
- **14 duplicate candidates**, genuinely caught by `dedupe.py`'s real `find_duplicate_of` — a
  case/trailing-slash url variant and a whitespace/case headline variant injected per batch, then
  merged via `CandidateRepository.merge` the same way a real duplicate would be.
- **1 candidate-level separation-of-duties exception** (`candidate_sod_exceptions`): one candidate
  is deliberately self-verified by its own capturer, authorised by the SIP Owner, so the exception
  path is exercised rather than only asserted.
- **RUN-SEED-05 leaves 56 of 112 mandatory sources uncovered** on purpose, so
  `missing_mandatory_outcomes()` has a real, non-empty answer; other runs that reach Scanning or
  later record the full mandatory set.
- **5 report versions** and **12 decision records** (CEO Ruling / Report Approval / Distribution
  Authority) across the QA Failed, Paused, Distributed and Stopped runs, plus one Report Drafted
  run left undecided on purpose (submitted, no decision yet — distinct from no report at all).
- A handful of `action_register`, `watch_lists`, `exceptions`, `comms_drafts` and `approved_facts`
  rows so the dashboard and comms UI aren't empty either.

## Why these numbers

Ten runs and roughly eighty candidates were picked to make the runs list and the busiest run's
candidate list (RUN-SEED-05, 20 rows) look like a system with a real spread of state, not a
fixture — while staying far short of `bench_indexes.py`'s 200-run/50k-candidate scale, which is
right for load-testing indexes and wrong for a walkthrough a person is meant to read.

## Rerunning

Idempotent by skipping, not by deleting. Every run, action, watch, exception, comms draft and fact
is keyed on a fixed code (`RUN-SEED-01`, `ACT-SEED-01`, ...); the script checks whether that code
already exists and skips the whole unit if so. This is not a stylistic choice: `report_versions`,
`decision_records`, `run_authorisations`, `sod_exceptions` and `candidate_sod_exceptions` all carry
an append-only/no-wipe trigger in `database/schema.sql` that refuses `UPDATE`/`DELETE` outright, so
a delete-and-recreate seed cannot work against this schema even in principle. `audit_log` rows are
append-only the same way and accumulate across reruns — that is the honest trail of the script
having run more than once, not a bug to hide.

## What this dataset is not

- **Not real operating history.** No real SIP-184 run has ever executed against this schema
  (`#55` is still open). Every headline, summary, comms draft and fact body is synthetic and
  tagged `[SEED]` for exactly that reason — none of it is a real news item, trade figure, member
  name or quote, per `PROJECT-RULES.md`.
- **Not a verified mapping of decision kind to state-machine gate.**
  `services/api/persistence.py`'s `apply_transition` only checks that the `decision_records` row
  named by `approval_ref` *exists* — it does not check that row's `kind` matches the gate's
  purpose. This script's choice of which decision kind stands in for which human gate (Report
  Approval for the QA sign-off gate, Distribution Authority for the two distribution gates, CEO
  Ruling for Stop/Pause) is a plausible reading of `apps/sip/core/orchestrator.py`'s gate table,
  not something the application enforces or that this script discovered by testing against a
  documented contract.
- **Not a substitute for the #337 evidence scripts.** `scripts/fta_corpus_report.py` and
  `scripts/sip_collector_pipeline_evidence.py` are the measured proof that the collector logic
  works; this script exists to make the UI layer look populated, not to re-prove the pipeline.
