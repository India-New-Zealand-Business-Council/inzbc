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
1. [`project-charter.md`](project-charter.md) — scope, objectives, roles, phase gates and the four
   decisions INZBC owns. The **proposed** shape of the engagement, in one page. It is not signed
   yet, so it is not yet client authority.
2. [`inzbc-ai-operating-system.md`](inzbc-ai-operating-system.md) — what INZBC is building and why.
3. [`architecture.md`](architecture.md) — system diagrams: context, components, run state machine,
   fail-closed controls, data model.
4. [`../CONTRIBUTING.md`](../CONTRIBUTING.md) and [`../CLAUDE.md`](../CLAUDE.md) — how work lands
   here: branch, PR, review, evidence block.
5. [`workstreams/README.md`](workstreams/README.md) — how the lanes are divided and who owns what.

## I am running SIP (analyst, reviewer or CEO)
- [`sip/operator-guide.md`](sip/operator-guide.md) — **start here.** One full day, in order, in
  plain language.
- [`sip/launch/`](sip/launch/) — the launch pack. `SIP-184` is the daily-run procedure, but the
  pack is at **v0.9 review draft and is not approved**: the only approved controlling document is
  `SIP-050 Master Prompt v1.1`. Treat `SIP-184` as the working procedure for the controlled launch,
  not as an approved instruction to act under.
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

## I am waiting on a client decision
- [`client-decision-pack.md`](client-decision-pack.md) — **start here.** The six decisions that
  belong to INZBC, in one place, each with what it costs to leave open. Between them they hold up
  17 tracked items.
- [`membership/member-jungle-assessment.md`](membership/member-jungle-assessment.md) — foundation
  decision F1: retain, integrate or replace Member Jungle. Blocks modules 2, 3 and 4, which is the
  largest block of unstarted work in the programme.
- [`project-charter.md`](project-charter.md) §11 and §18 — the four foundation decisions and the
  open items INZBC owns.

## I am handling data
- [`data/system-of-record-and-retention.md`](data/system-of-record-and-retention.md) — where each
  data type authoritatively lives, how it is classified, and how long it may be kept. Starts with
  the fact that the system holds no member data at all today, which is what makes the controls
  cheap to put in now and expensive to retrofit later.

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

## I am working on the Wix site
- [`studio-build-spec.md`](studio-build-spec.md) — the build spec for the Studio site: tokens,
  page tree, slugs, content rules, and the checklist that gates the first republish.
- [`website-rebuild-plan.md`](website-rebuild-plan.md) — **read first.** What the rebuild
  does in what order, the Editor versus Studio decision that governs it, and which external
  research findings survived checking.
- [`wix-staging-readiness.md`](wix-staging-readiness.md) — **read first.** What is verified on the
  duplicate, what cannot be scripted, and why publishing it before the content is real is the
  thing to avoid.
- [`website-redirect-map.md`](website-redirect-map.md) and
  [`wix-rebuild-decisions.md`](wix-rebuild-decisions.md) — the URLs and the decisions behind them.
- [`wix-changes-log.md`](wix-changes-log.md) — every editor session, before and after text.

## Background and client context
- [`discovery.md`](discovery.md) — the original discovery work.
- [`ai-service-architecture.md`](ai-service-architecture.md) — why the AI layer is hosted separately
  from the website platform.
- [`client-comms-drafts.md`](client-comms-drafts.md) — client-facing drafts.
- `inzbc-talking-points.md`, `sunil-requests.md` and `services-agreement-draft.md` are gitignored
  and exist only on the author's machine. They are named here so their absence is deliberate rather
  than a gap, and are not linked because the link resolves for nobody else.

---

## Repositories

Three of them. [`repositories.md`](repositories.md) explains what each holds, why they are separate,
and how to open a session that can see all three at once.

| Repository | Holds |
|---|---|
| `inzbc` (this one) | The platform, the shared contracts, and all controlled documentation |
| `daily-india-nz-news-agent` | The collection engine behind the daily digest, draft-only |
| `inzbc-studio-site` | The Wix Studio website. Wix pushes to this one too |

The short version: the collection engine reaches untrusted sources on a schedule, and Wix owns the
structure of the site repository and pushes to it. Neither belongs inside the repository holding the
shared contracts and the documents of record.

**Controlled documents live here and nowhere else.** The other two link to them rather than copying
them.
