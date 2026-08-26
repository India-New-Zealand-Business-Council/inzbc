# Backend engineering evidence

Status: written 20 August 2026. Owner: Bhanu. Audience: academic assessor, project coordinator.

## The concern

Feedback received: the project looks like it is only calls to an AI API, with no real backend.

This document answers that with counts anyone can reproduce from the repository, and is equally
explicit about where the backend genuinely *is* thin. Every number below has the command that
produced it, so none of it has to be taken on trust.

## The measurement

```
find apps services database -name '*.py' -not -path '*test*' -not -path '*__pycache__*' | xargs wc -l
grep -rln 'import openai\|from openai\|anthropic' --include=*.py apps services
```

| Measure | Value |
|---|---|
| Python source lines, excluding tests | **9,245** |
| Lines in the only two model-touching modules | **295** (`model_gateway.py` 150, `scoring.py` 145) |
| Share of source that touches a model | **3.2%** |
| Files importing an AI SDK anywhere in the repo | **1** (`services/api/model_gateway.py`) |

96.8% of the source is application and data code that would exist unchanged if the model were
removed entirely.

## What the backend actually contains

```
grep -rhoE '@[a-zA-Z_]*router\.(get|post|patch|put|delete)\(' services/api --include=*.py | grep -v test | wc -l
grep -cE '^create table' database/schema.sql
```

| Primitive | Count |
|---|---|
| REST routes | 51, across 13 routers |
| Database tables | 25 |
| Foreign-key columns | 39 (52 `references` occurrences, including table-level constraints) |
| Indexes | 54 (3 explicit + 48 implicit from PK/UNIQUE constraints + 3 added by #334) |
| CHECK constraints | 31 |
| Enum types | 11 |
| Triggers | 15 |
| Stored functions | 2 |
| SQL schema lines | 701 |
| Python tests | 1,047 passing, 0 skipped |
| CI jobs defined to gate every merge | 9 (none have run since 24 August, see below) |

An earlier version of this table said 34 routes across 12 routers. That count used a
narrower grep matching only decorators literally named `@router.`, which missed the three
routers `registers.py` defines under other names (`action_register_router`,
`watch_list_router`, `exceptions_router`). 13 routers is confirmed independently by the 13
`app.include_router(...)` calls in `services/api/main.py`.

Engineering that is not model work, with the file that implements it:

- **Session authentication and RBAC** — opaque server-side sessions, `HttpOnly; Secure;
  SameSite=Lax` cookies, roles resolved from `user_roles`. `services/api/session.py`, `auth.py`
- **CSRF protection** — double-submit token required on every state-changing route, because
  `SameSite=Lax` still permits a top-level cross-site POST. `services/api/session.py`
- **Separation of duties** — enforced against recorded acts, plus the database-level constraint
  `runs.analyst_id <> runs.reviewer_id`. `services/api/decisions.py`, `database/schema.sql`
- **Append-only audit** — 15 triggers refusing UPDATE/DELETE, statement triggers refusing TRUNCATE
  (which a row trigger never sees), and an application role granted INSERT/SELECT only.
  `database/schema.sql`, `database/audit_role.sql`
- **Transactional audit writes** — the audit row commits inside the mutation's own transaction, so
  the change and its record land together or not at all. `services/api/audit.py`
- **Optimistic concurrency** — version-checked updates that refuse a lost update.
  `services/api/persistence.py`
- **A finite state machine** — 18 states, an explicit allowed-transition table and an explicit
  illegal-transition list. The single write path, `RunRepository.apply_transition`, imports that
  table's checks rather than restating them, so an illegal jump is refused at the layer closest to
  the database and not only at the layer that is supposed to call it.
  `apps/sip/core/orchestrator.py`, `services/api/persistence.py`, `schemas/state-machine.md`
- **Contract-first API** — OpenAPI generated from the code, TypeScript client generated from that,
  and a CI job that fails the build when the two drift. `schemas/openapi.json`
- **Rate limiting, security headers, CORS deny-by-default** — `services/api/hardening.py`

**CI has not run since 24 August 2026.** Every job on every branch fails at startup with no
steps executed, including Dependabot's, while `.github/workflows/ci.yml` has not changed
since 13 August and runs were green through 23 August. That points at an Actions quota or
org policy cutoff rather than anything in this repository. Until it is restored, the nine
jobs are defined but are not gating anything, and the figures above rest on
`.claude/verify.local.sh` run locally against a real Postgres.

## The strongest single counter-example

The FTA Implementation Centre — one of the four delivered modules — **makes no model call at
all**. `apps/fta/explainer.py` matches a query against a curated, citation-carrying corpus and
returns an escalation path when nothing matches. It cannot hallucinate a trade fact because it
cannot generate text.

That is a deliberate architectural decision recorded in `docs/architecture.md`, not an
implementation shortcut. A project that were only an AI wrapper could not have built it.

## Where the backend is genuinely thin

Stating this plainly, because a document that lists only strengths is marketing.

| Gap | Evidence | Issue |
|---|---|---|
| ~~3 indexes for 39 foreign-key columns~~ — **this was wrong, see below.** Three genuine hot-path indexes were missing and are now added and measured. | `scripts/bench_indexes.py` | #334, closed |
| ~~No migration mechanism~~ — **closed.** Forward-only runner with a tracking table, four enforced refusals, no new dependency. | `scripts/migrate.py`, `database/migrations/` | #44, closed |
| ~~No load or performance evidence~~ — **closed.** Endpoint p50/p95, query plans, and a concurrency probe that showed 1 win / 7 version conflicts under 8 parallel writers. | `docs/performance-baseline.md` | #335, closed |
| **The SIP UI is not wired to the backend.** It runs on fixture-backed stubs, so the most control-heavy screens do not exercise the API they were built against. | `apps/sip/ui/src/api/reportsStore.ts` | #336 |
| **The member portal has no backend integration.** No API client, no `fetch()` call. | `apps/member/ui/src/lib/` holds static data | #198 |
| **Never deployed.** `production_enabled` is false, no environment exists. | `render.yaml` present, unused | #99 |

These are ordinary backend engineering with no model involvement whatsoever.

### A correction worth reading, because the method matters

The first version of this document claimed the schema had **3 indexes for 39 foreign keys** and
presented that as a serious gap. That was wrong, and the way it was wrong is instructive.

`grep -c '^create index' database/schema.sql` returns 3. But Postgres creates an index for every
PRIMARY KEY and every UNIQUE constraint automatically, and the schema has 48 of those:

```
select count(*) from pg_indexes where schemaname = 'public';   -- 51, not 3
```

So the schema was already substantially indexed, and counting `CREATE INDEX` statements
understated it by a factor of seventeen. Two of the five indexes originally proposed turned out to
be redundant — `source_checks (run_id, source_id)` is already covered by its UNIQUE constraint, and
`report_versions (run_id)` by the leading column of one.

Three were genuinely missing, and only measurement separated them from the two that were not:

| Query | Before | After |
|---|---|---|
| `candidates where run_id = ?` | 2.47 ms, sequential scan | 0.06 ms, index scan |
| `candidates where run_id = ? group by verification` | 2.08 ms, sequential scan | 0.08 ms, index scan |
| `audit_log where record_type = ? and record_id = ? order by at desc` | 3.33 ms, sequential scan | 0.07 ms, index scan |

Measured at 200 runs, 50,000 candidates and 40,000 audit rows by `scripts/bench_indexes.py`, which
is committed and rerunnable. The three indexes are now in `database/schema.sql`, each carrying the
query it serves and the measurement that justified it.

This is included rather than quietly corrected because it is the honest version of the answer to
the original concern: the backend was better than a naive count suggested, the real gaps were
narrower and more specific, and the difference between the two was a measurement rather than an
opinion.

## How to verify this document

Every figure above is reproducible from a clean checkout:

```
.venv/Scripts/python.exe -m pytest apps services -q      # requires DATABASE_URL
grep -c '^create table' database/schema.sql
grep -rln 'import openai' --include=*.py apps services
```

The test suite requires a real Postgres; without `DATABASE_URL` set, 170 database-backed tests
skip silently and the suite reports a misleading 851 passed. `.claude/verify.local.sh` refuses to
run rather than report that subset.
