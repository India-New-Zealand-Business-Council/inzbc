# SIP Platform Build Plan (3-person, independent workstreams)

Team: **Bhanu** (tech lead), **Roshan**, **Paras**. Goal: build the SIP control-plane app around
the existing collection agent. Split so all three work in parallel without touching the same
files. Grounded in the real Intelligence Database v1.9 model, SIP-050 v1.1, and the launch brief.

## The rule that keeps work independent
Everyone builds against **shared contracts**, not shared files:
1. **DB schema** (tables + columns) — the single source of truth for data shape.
2. **API contract** (OpenAPI) — every endpoint's request/response, agreed up front.
3. **State model** — the allowed run states + transitions.

Bhanu writes these three first (Days 1-2). After that, Roshan and Paras code in their **own
folders** against the contracts. They only meet at the DB + API boundary, never in the same file.

Repo layout (brief §15), owners in brackets:
```
/inzbc-sip
  /database      (Bhanu)   schema, migrations, seed
  /schemas       (Bhanu)   shared types, API contract (OpenAPI)
  /api/core      (Bhanu)   auth, RBAC, audit, state machine
  /api/pipeline  (Roshan)  run, sources, candidates endpoints
  /api/control   (Paras)   brief, QA, approval, registers endpoints
  /agents        (Roshan)  wire the existing collection agent
  /app/pipeline  (Roshan)  run control, source worklist, candidates UI
  /app/control   (Paras)   brief builder, QA, approval, registers, dashboard UI
  /deployment    (Bhanu)   CI, environments, backup jobs
  /tests         (all, per own module)
```

## Workstream A — Bhanu (tech lead): foundation + cross-cutting
Owns the shared contracts and the risky/security parts. Front-loaded so it unblocks the others.
- Scaffold repo, environments (Dev/Test/Controlled-Launch/Prod), CI.
- **DB schema + migrations** from the v1.9 model (Runs, Candidates, Daily Intelligence, Action
  Register, Watch Lists, Source Library, Approval & Distribution, Audit, Exceptions, etc.).
- **API contract** (OpenAPI) for every endpoint the other two implement.
- **State machine** (Draft -> ... -> Distributed/Closed) with illegal-transition guards.
- **Auth + RBAC** (roles from launch-config), separation of analyst vs reviewer.
- **Audit log** (append-only) + the disabled-controls flags enforced server-side.
- Deployment, secrets wiring (when supplied), backup jobs, integration + review of A/B/C.
- **Definition of done:** contracts published Day 2; auth/audit/state/CI green; server-side
  control flags enforced; the other two can run their modules against a live schema + API.

## Workstream B — Roshan: intelligence pipeline (data in)
Produces data into the DB via the API. No UI overlap with Paras.
- Wire the **existing collection agent** as the collector (it already fetches/scores/drafts).
- **Run control:** create authorised run, lock 24h coverage window, load version set.
- **Source worklist + outcomes** (SIP-185): record an outcome per mandatory source + fallbacks.
- **Candidate capture** (all fields) + relevance/signal/confidence + verification + dedupe.
- Pipeline endpoints under `/api/pipeline`, UI under `/app/pipeline`.
- **Definition of done:** a run can be opened, window locked, sources recorded, candidates
  captured and written to the DB through the API. No writes to control-plane tables.

## Workstream C — Paras: human control + output (data out)
Consumes data from the DB via the API. No pipeline overlap with Roshan.
- **Daily Brief builder** (SIP-186 structure) from selected candidates.
- **QA control** (SIP-188): independent reviewer, block release on Critical.
- **Approval & distribution:** CEO decision form, manual-send package, recipient allowlist,
  no auto-send (server flag stays false).
- **Registers UI:** Action Register (DB is authority), Watch Lists (ACT-009, WL-006),
  Opportunities, Threats; Exceptions/Corrections (SIP-189); Executive Dashboard.
- Control endpoints under `/api/control`, UI under `/app/control`.
- **Definition of done:** a drafted brief can be QA'd, approved by the CEO, and produce a
  manual-send package, with all register views reading the DB. No pipeline writes.

## Sequence
- **Days 1-2 (Bhanu):** contracts (schema + API + state) + repo + CI. Blocks nothing after.
- **Days 3+ (parallel):** Roshan builds pipeline; Paras builds control/UI; Bhanu builds
  auth/audit/security/deploy + integrates.
- **Weekly:** Bhanu reviews + merges to main (PRs only). Contract changes go through Bhanu.

## Non-negotiables (all workstreams)
- Server-side control flags stay false: automated/member/external/website/social distribution.
- Human approval before any distribution. Fail-closed on Critical conditions.
- No secrets in code/logs/repo. No AI attribution in commits/PRs.
- Every controlled action writes an audit row.

## Not in scope for the 5-day launch
This app is Phase 2. The **27-31 July launch runs manually** on the current DB workbook + agent
using the v0.9 launch pack. The app replaces the manual process after it is built and reviewed.
