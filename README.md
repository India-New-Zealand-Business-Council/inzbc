# INZBC AI Operating System (AIOS)

One governed operating environment for the India New Zealand Business Council: a public and
member website, a controlled Strategic Intelligence Platform (SIP), an FTA implementation centre,
staff AI assistants, and the membership/sponsor/trade-service records behind them. Delivered by a
three-person team (Bhanu Gupta, Roshan Aryal, Paras) via an AIC / Otago Polytechnic placement.

Full brief: [docs/inzbc-ai-operating-system.md](./docs/inzbc-ai-operating-system.md).

## Scope
**In:** public website, member portal, SIP (intelligence + collection + review/approval), FTA
centre + Explainer, AI Communications Assistant, membership/sponsor/trade-service records, events
and delegations, executive/board dashboards, and the security/audit/backup/handover around them.

**Out (separate projects):** WIA, Kiwi Indians (kiwiindians.nz), WAIP, any personal site, and
political systems. No data is shared between organisations without a documented lawful purpose.

## Status
- **Phase 0 — SIP controlled launch, 27–31 July 2026:** ran manually on the Intelligence Database
  workbook + the collection agent + the v0.9 launch pack. Complete.
- **Phase 2 — app build, in progress.** [ADR-0004](./docs/decisions/0004-platform-graduation.md)
  graduated the platform from a scheduled process to an always-on hosted service with managed
  Postgres, ahead of formal client sign-off, against the resolution it records for the four
  foundation decisions. Merged so far: the SIP run lifecycle (`/api/runs`), candidate command
  endpoints (`/api/candidates`), transactional append-only audit, a decision/approval/distribution
  record layer ([ADR-0005](./docs/decisions/0005-decision-approval-distribution.md)), and a member
  portal UI shell.
- **Formal sign-off is still open.** The four foundation decisions themselves
  (`docs/client-answers.md` E1) are tracked as `PROPOSED`, not yet confirmed by INZBC — the team is
  building against ADR-0004's documented resolution of them in the meantime, not against a signed
  client decision. Treat that distinction as live until it closes.

Nothing is in production. Automated distribution and public publishing stay disabled behind human
review (`production_enabled = false`).

## Operating principles
- **INZBC owns the system** — accounts, domains, data and recovery live in INZBC-owned accounts.
- **Humans approve high-impact actions** — no AI publishes, emails, or changes controlled records
  without a named human approval.
- **One system of record per data type.** Do not duplicate the member/payment register.
- **Build only after decisions** — no engineer fills an unresolved business rule with a technical
  assumption.

## Repository layout (monorepo)
```
/apps/site        site (Velo) + content specs
/apps/sip         SIP control app: collection, orchestrator, pipeline
/apps/fta         FTA Explainer service + corpus
/apps/comms       Communications Assistant
/apps/member      Member portal UI shell
/services/api     FastAPI app: run + candidate endpoints, decisions, audit, redaction, hardening
/database         schema + migrations
/schemas          shared types + API contract
/docs             planning + governance (proposal, discovery, sip, workstreams, …)
```
The `daily-india-nz-news-agent` repo stays separate — it is the SIP collection engine. New repos
only when a component genuinely needs isolation; the monorepo is the default.

## The live site and membership
- `inzbc.org` runs on Wix and is **not edited directly**. The new site is built separately and
  replaces the live one at go-live only, after a backup and explicit sign-off.
- Membership currently runs on **Member Jungle**. Do **not** rebuild membership on Wix before the
  retain / integrate / replace assessment. Member Jungle is the provisional system of record.

## Working on this repo
See [CONTRIBUTING.md](./CONTRIBUTING.md) and the team workflow in
[docs/workstreams/README.md](./docs/workstreams/README.md). Short version: work from your worklog,
branch, open a PR into `main` to the quality standard; Bhanu reviews and merges. No direct pushes
to `main`.

## Key documents
Full index, organised by what you're trying to do: [`docs/README.md`](./docs/README.md).
- Programme brief: `docs/inzbc-ai-operating-system.md`
- Project charter + the four foundation decisions: `docs/project-charter.md`
- What's waiting on an INZBC decision: `docs/client-decision-pack.md`
- Module map (full scope): `docs/modules/README.md`
- Architecture decisions (ADRs): `docs/decisions/`
- Discovery, IA, risks: `docs/discovery.md`
- Site page specs: `docs/page-specs.md`
- FTA source corpus: `docs/fta-source-corpus.md`
- SIP spec + config: `docs/sip/` · SIP build plan: `docs/sip/build-plan.md`
- Team workflow + worklogs: `docs/workstreams/`
