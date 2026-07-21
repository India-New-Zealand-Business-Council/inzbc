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
- **Phase 0 — SIP controlled launch, 27–31 July 2026:** runs **manually** on the current
  Intelligence Database workbook + the collection agent + the v0.9 launch pack. Human approval
  each day. No app required.
- **Phases 1–4 (app build):** phased and **gated** — nothing past Phase 0/1 builds until INZBC
  signs the four foundation decisions (membership platform, internal platform, identity model,
  budget/ownership).

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
/apps/sip         SIP control app
/apps/fta         FTA Explainer service + corpus
/apps/comms       Communications Assistant
/services/api     shared API, auth, audit
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
- Programme brief: `docs/inzbc-ai-operating-system.md`
- Module map (full scope): `docs/modules/README.md`
- Discovery, IA, risks: `docs/discovery.md`
- Site page specs: `docs/page-specs.md`
- FTA source corpus: `docs/fta-source-corpus.md`
- SIP spec + config: `docs/sip/` · SIP build plan: `docs/sip/build-plan.md`
- Team workflow + worklogs: `docs/workstreams/`
