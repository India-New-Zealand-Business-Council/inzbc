# Documentation index

Start here. Documentation is organised by what you are trying to do, not by which team wrote it.

Two conventions hold across this tree:
- **Controlled documents live in exactly one place.** The SIP operating documents live in
  `sip/launch/` and nowhere else. Copies drift, and a drifted controlled document is worse than no
  copy at all.
- **The doc is updated in the same pull request as the change it describes.** Documentation that
  lags the code stops being documentation and becomes folklore.

---

## I am new to the project
1. [`inzbc-ai-operating-system.md`](inzbc-ai-operating-system.md) — what INZBC is building and why.
2. [`architecture.md`](architecture.md) — system diagrams: context, components, run state machine,
   fail-closed controls, data model.
3. [`../CONTRIBUTING.md`](../CONTRIBUTING.md) and [`../CLAUDE.md`](../CLAUDE.md) — how work lands
   here: branch, PR, review, evidence block.
4. [`workstreams/README.md`](workstreams/README.md) — how the lanes are divided and who owns what.

## I am running SIP (analyst, reviewer or CEO)
- [`sip/operator-guide.md`](sip/operator-guide.md) — **start here.** One full day, in order, in
  plain language.
- [`sip/launch/`](sip/launch/) — the controlled documents themselves. `SIP-184` is the procedure of
  record; the operator guide is its plain-language companion.
- [`sip/README.md`](sip/README.md) — SIP scope, non-negotiables and control boundary.

## I am building a module
- [`requirements.md`](requirements.md) — user stories with acceptance criteria, the non-functional
  requirements every story is bound by, and the traceability matrix linking each requirement to the
  code and tests that satisfy it.
- [`modules/`](modules/) — one spec per module: website, membership CRM, member portal, comms
  assistant, FTA centre, dashboards, events and delegations, sponsors and trade services.
- [`../schemas/api-contract.md`](../schemas/api-contract.md) — the REST contract both pipeline and UI
  build against.
- [`../schemas/state-machine.md`](../schemas/state-machine.md) — the run states and legal
  transitions, enforced in `apps/sip/core/orchestrator.py`.
- [`../database/schema.sql`](../database/schema.sql) — the data model. An entity diagram of it is in
  [`architecture.md`](architecture.md).

## I need to know why something was decided
- [`decisions/`](decisions/) — architecture decision records. Each states the context, the options
  compared, the decision and its consequences.
  - `0001-backend-language.md` — Python, FastAPI and Pydantic for the backend.
  - `0003-frontend-tooling.md` — Storybook, Vitest, Playwright and Chromatic, with the paid
    alternatives explicitly rejected on cost.

  A significant technical decision is recorded here **with the alternatives considered**, not
  announced after the fact.

## I am writing content or an AI-drafted output
- [`information-standard.md`](information-standard.md) — the approved INZBC disclaimer and the
  Information Confidence Standard every AI answer carries.
- [`fta-source-corpus.md`](fta-source-corpus.md) — the sourced FTA facts, with what is confirmed and
  what is explicitly not.
- [`page-specs.md`](page-specs.md) — public page specifications.

  The rule that governs all of it: **no invented statistics, board names or FTA details.** Sourced
  material only, `[[placeholders]]` where a fact is owed by INZBC, and a named human reviewer before
  anything publishes.

## Background and client context
- [`discovery.md`](discovery.md) — the original discovery work.
- [`ai-service-architecture.md`](ai-service-architecture.md) — why the AI layer is hosted separately
  from the website platform.
- [`inzbc-talking-points.md`](inzbc-talking-points.md), [`sunil-requests.md`](sunil-requests.md),
  [`client-comms-drafts.md`](client-comms-drafts.md) — client-facing material and requests.
- [`services-agreement-draft.md`](services-agreement-draft.md) — engagement terms draft.

---

## Repositories

| Repository | Holds |
|---|---|
| `inzbc` (this one) | The platform, the shared contracts, and all controlled documentation |
| `daily-india-nz-news-agent` | The collection engine that runs the live daily digest |

The collection engine is deliberately separate: it has its own release cadence and runs on a
schedule, while this repository holds the platform and the documents of record.
