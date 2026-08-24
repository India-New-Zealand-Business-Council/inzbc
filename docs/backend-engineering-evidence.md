# Backend engineering evidence

Referenced by issue #329 (container diagram) and #330 (integration-pattern diagrams): the single
source for the counts those diagrams annotate `services/api` and Postgres with. Every number below
has the exact command that produced it, run against this repository, so a diagram can cite this
document instead of retyping a number nobody can re-check. If a count has drifted by the time you
read this, re-run the command and fix the number here first — the diagrams should follow this
document, not the other way round.

Written directly in response to the assessment feedback recorded on #329: "the project reads as an
AI API wrapper with no real backend." The counts below are the rebuttal — a thin wrapper around one
model call does not have 50 routes, 25 tables, RBAC, CSRF, an append-only audit trail, and a state
machine enforced by database triggers.

## services/api

**Routes and routers**, counted from the `@router.get/post/patch/put/delete` decorators:

```
grep -rhoE '@[a-zA-Z_]*router\.(get|post|patch|put|delete)\(' services/api --include=*.py | grep -v test | wc -l
```
→ **50 routes**

```
grep -rn '= APIRouter(' services/api --include=*.py | grep -v test | wc -l
```
→ **13 routers** (11 files; `registers.py` alone defines three — `action_register_router`,
`watch_list_router`, `exceptions_router` — confirmed against `services/api/main.py`'s 13
`app.include_router(...)` calls, one per router).

Per file: `candidates.py` 7, `comms.py` 4, `dashboard.py` 1, `facts.py` 6, `oauth.py` 2,
`registers.py` 12, `reports.py` 3, `runs.py` 10, `session.py` 2, `source_checks.py` 2,
`source_library.py` 1.

*(#329's comment cites "34 routes across 12 routers" — that was this repository's shape on 20
August; 16 routes and one router (`oauth.py`, the GitHub sign-in handshake, #42) were added since.
The numbers above are current as of this document, not the comment.)*

**Cross-cutting layers** — applied to every route through shared dependencies and middleware, not
re-implemented per router:

| Layer | Where | What it does |
|---|---|---|
| Session auth | `services/api/session.py:103` (`require_principal`) | Reads the `inzbc_session` cookie, resolves it to a `Principal` server-side — opaque session, not a JWT (ADR-0004) |
| CSRF | `services/api/session.py:127` (`require_csrf`) | Double-submit `X-CSRF-Token` header required on every `POST`/`PUT`/`PATCH`/`DELETE` |
| RBAC | `services/api/session.py:216` (`read_access`), `:230` (`write_access`), `services/api/auth.py:292` (`require_roles`) | Per-route allowed-role lists, checked against `user_roles`, not trusted from the caller |
| Rate limiting | `services/api/hardening.py:60` (`RateLimiter`), installed at `:150` | Per-client-key request cap; breach returns 429 with `Retry-After` |
| Security headers | `services/api/hardening.py:163-166` | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Cross-Origin-Opener-Policy: same-origin` — set on every response, API and served UI alike |
| CORS | `services/api/hardening.py:169-179` | Deny-by-default: empty/unset `CORS_ALLOWED_ORIGINS` means no cross-origin access at all; opt-in only, `GET`-only, no credentials when enabled |
| Error envelope | `services/api/hardening.py:120-148` | Three exception handlers (`HTTPException`, `RequestValidationError`, bare `Exception`) — the unhandled-exception one never returns the exception text, so a stack detail or connection string can't leak to a caller |

## Postgres (`database/schema.sql`)

Counted against a **freshly created database with `schema.sql` applied from a clean state**, not an
existing dev database that may have drifted from local testing:

```
docker exec <postgres-container> psql -U inzbc -d postgres -c "create database inzbc_evidence_check;"
docker cp database/schema.sql <container>:/tmp/schema.sql
docker exec <postgres-container> psql -U inzbc -d inzbc_evidence_check -f /tmp/schema.sql
```

Then, against `inzbc_evidence_check`:

| Count | Query | Result |
|---|---|---|
| Tables | `select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE';` | **25** |
| Indexes | `select count(*) from pg_indexes where schemaname='public';` | **51** |
| Foreign-key constraints | `select count(*) from information_schema.table_constraints where constraint_type='FOREIGN KEY' and table_schema='public';` | **50** |
| Foreign-key columns | `select count(*) from information_schema.key_column_usage k join information_schema.table_constraints t on k.constraint_name = t.constraint_name and k.constraint_schema = t.constraint_schema where t.constraint_type='FOREIGN KEY' and t.table_schema='public';` | **69** |
| CHECK constraints | `select count(*) from information_schema.table_constraints where constraint_type='CHECK' and table_schema='public' and constraint_name not like '%_not_null';` | **31** |
| Enum types | `select count(distinct t.typname) from pg_type t join pg_enum e on t.oid = e.enumtypid;` | **11** |
| Triggers | `select count(*) from information_schema.triggers where trigger_schema='public';` | **15** |

*(#329's comment cites "39 foreign-key columns" and "54 indexes" — a static text search against the
DDL file undercounts indexes, since Postgres creates one automatically for every `PRIMARY KEY` and
`UNIQUE` constraint without a separate `CREATE INDEX` line to grep for. Querying the actual catalog
of a freshly built database, as above, is the more reliable method and is what these numbers use.)*

Why this matters for the "AI wrapper" argument: 31 `CHECK` constraints and 15 triggers are
enforcement, not storage — e.g. `runs_check1` (`database/schema.sql`) refuses a run where
`analyst_id = reviewer_id` at the database layer, not just in application code, and the audit-log
triggers block `UPDATE`/`DELETE` on `audit_log` outright so an append-only trail is a database
guarantee, not a convention a bug could quietly break.

## The model provider is one narrow edge, not the centre

```
grep -rln "from services.api.model_gateway\|model_gateway\." --include=*.py services apps | grep -v test
```
→ exactly three call sites: `services/api/comms.py`, `apps/comms/draft.py`,
`apps/sip/core/scoring.py`. Every model call in the platform goes through one gateway module
(`services/api/model_gateway.py`) — there is no second path to the model provider anywhere in the
codebase.

```
grep -rln "openai\|anthropic\|model_gateway" apps/fta --include=*.py --include=*.ts --include=*.tsx
```
→ no matches. The FTA Explainer makes **zero** model calls — it answers only from a sourced corpus.
This is the dashed "no model call" edge in `docs/architecture.md` §1, and per #329's comment it
should stay visually prominent in the container diagram rather than being one dashed line among
many: it's the single strongest counter-example to "AI wrapper with no real backend," because it's
proof the platform's own design keeps the model *out* of a whole product surface where it isn't
needed.

## Related documents
- `docs/architecture/containers.md` — the container diagram these numbers annotate
- `docs/architecture.md` — system context and SIP component diagrams
- `database/schema.sql` — schema source
- `schemas/api-contract.md` — the route contract
