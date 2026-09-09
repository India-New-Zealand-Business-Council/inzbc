# Changelog

Notable changes per release. Dates are New Zealand time.

This file records what changed and why it mattered, not every commit — the commit log is the
complete record. Nothing here is deployed anywhere: `production_enabled` is `false` and no release
below is a SIP-184 production run.

## [v1.0.0] — 2026-09-10

First full release. One application. Four modules on one governed backend — trade intelligence
(SIP), FTA guidance, communications drafting and member services — reachable from a single nav
rather than five dev servers.

### Changed

The substance of this release is the removal of stand-ins. The SIP workflow screens act on a run
chosen from the database, load that run's candidates, gate on that run's recorded state, and hash
what was actually selected when a brief is submitted. Every one of those was a fixture before.

- Run selection lifted into the shell: **Work this run** under Runs & Candidates decides which run
  the Brief Builder, QA Review, CEO Decision and Distribution screens act on, and each names it.
- The run archive lists the runs actually recorded (`GET /api/runs`), with `qa_status` newly
  exposed on `RunOut`. Null renders as *not yet run* — a run that has not reached QA has no result
  to report, which is a third fact rather than a missing one.
- Seeded candidates carry a proposed routing derived from their topic, so the routing step reads
  as the decision it is rather than a column of `Unrouted`.
- The Platform Overview's counts are re-derived, and the command that produces each is recorded
  beside it. Four of the six had drifted.

### Fixed

Each of these was found by running the system rather than reading it.

- **`QA Failed` had no exit.** `schemas/state-machine.md` allows exactly one edge out of it and
  `orchestrator.py` marks that edge human-gated, but no route implemented it — so a run that failed
  QA was stuck at the one state the specification calls recoverable. Added
  `POST /api/runs/{id}/return-for-correction`, Reviewer or SIP Owner, matching `fail-qa`.
- **Submitting a brief answered 500.** One field carried both the run number a person reads and
  the UUID that three writes validate; it held the number, so `SubmitReportIn.run_id` failed inside
  psycopg rather than as a validation error. `runId` and `runNumber` are now separate.
- **The submitted content hash covered an empty digest.** Selected candidate ids were resolved
  against a fixture whose ids (`cand-1`) cannot match a live candidate's UUID, so nothing ever
  matched and every brief was hashed as if it contained nothing. The hash is the whole durable
  record of what was submitted. A selected id that cannot be resolved is now refused rather than
  dropped, because a digest quietly short of an item still produces a plausible hash.
- **The Brief Builder showed the wrong run's candidates.** It fetched `runs[0]` while the header
  showed the selected run, so it could display one run's candidates under another run's number —
  and, after the digest fix, hash them against the selected run's id.
- **The seed could permanently corrupt its own dataset.** `create_run` commits before the state
  walk starts, so an interrupted seed left a run at `Draft`; the existence check then skipped that
  run on every later re-seed and reported success over the top. Two of the ten demonstrated states
  were wrong because of it, and no amount of re-seeding could fix them. The seed now refuses, and
  names a fresh database as the fix.

### Known and unresolved

- `test_walk_full_run` fails intermittently against a long-lived local database (three of five
  full-suite runs). It does not reproduce against a fresh one, and CI builds a fresh database per
  run and has been green throughout. Recorded rather than closed: the cause is not proven.
- Separation of duties is enforced against recorded acts rather than job titles, but one person
  currently holds every role, so most runs would proceed through a recorded `sod_exceptions` row.
  That is the control working for a single-operator organisation, not a workaround.
- Formal client sign-off on the four foundation decisions is still open (`docs/client-answers.md`
  E1). The build follows ADR-0004's documented resolution of them, not a signed decision.

### Scale at this release

60 REST operations across 51 paths · 26 tables, 50 foreign keys, 31 CHECK constraints · 15
append-only triggers · 1,188 Python tests and 410 frontend tests · 9 CI jobs gating every merge ·
1 file importing an AI SDK, of roughly ten thousand lines.

## [v0.1.0] — 2026-09-09

First tagged release: the SIP decision gate and the release predicate it had not previously
enforced, the four module UIs matched to the live design system, and the platform runner that
brings the whole system up with one command.
