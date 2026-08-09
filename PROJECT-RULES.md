# Contributor guidelines — INZBC platform

Repo-specific rules. General workflow is in [CONTRIBUTING.md](./CONTRIBUTING.md).

## Content

- Executive tone: professional, data-driven, politically neutral. No AI clichés.
- **Never invent** statistics, member counts, board names, or FTA details. Use sourced
  material only; leave `[[placeholders]]` where facts are owed by INZBC.
- Every AI-drafted output (digest, explainer, comms) needs a **named human reviewer** before
  publishing. `production_enabled` stays `false` until a formal launch approval exists.
- Handle member/personal data per the NZ Privacy Act 2020.

## The live site

- **Do not edit or publish `inzbc.org`.** Build on the duplicate site; cut over at go-live only,
  after Sunil signs off in writing. Publish rights stay with Sunil as account owner.
- Build work happens on the **duplicate** of the live site (`docs/discovery.md` OI-9). Only the
  account owner can duplicate a site. Duplication does not copy everything — app data, contacts
  and some settings do not come across — so never assume CMS or member data followed.
- **Not everything waits for publish.** Content Manager (CMS) collections and some app data take
  effect independently of the editor's save/publish split. Wix MCP writes hit **live data
  instantly** — no draft. Do not point write calls at the live site.
- "Take a full backup" is not a thing on Wix; there is no complete external site backup. Before
  cutover: record the Site History version and export CMS collections where applicable.
- Site History restores saved page versions, so page edits are recoverable. It is not a general
  safety net: apps, some components and CMS data may not restore cleanly.
- Log every Wix editor session in `docs/wix-changes-log.md`, on the duplicate as well as the live
  site — before and after text for each change, not just the section name. Site History records
  *that* something changed; the log records what it said and where the facts came from.
- A publish guard hook (`wix-no-publish.sh`) was previously cited here as blocking MCP publishes.
  It is **not implemented**. A hook could only ever stop MCP-driven publishes; a person clicking
  Publish is stopped by Wix roles, not by anything in this repo.

## Membership and data
- Membership runs on **Member Jungle** (provisional system of record). Do **not** rebuild
  membership on Wix before the retain/integrate/replace assessment. Link out; do not duplicate.
- One system of record per data type; never maintain the member or payment register in two places.
- Build only after the business rule is decided. Do not fill an unresolved rule with an assumption.

## SIP (Trade Intelligence Platform)

- It is a **code application, not a Wix build** (Postgres, server-side model calls, auth,
  audit). See [docs/sip/README.md](./docs/sip/README.md). Security review before any staff use.

## Git

- Branch, open a PR into `main`. No direct pushes to `main`; only Bhanu merges.
- Imperative commit subjects under ~60 chars. No AI attribution in commits, PRs, or code comments
  — matching [CONTRIBUTING.md](./CONTRIBUTING.md). The rule is about **authorship of delivered
  work**: a human is accountable for every change, so nothing credits a tool as its author.
  It is not a ban on AI tooling, and `PROJECT-RULES.md`, `AGENTS.md` and `.claude/` are deliberately
  tracked — configuration that makes the tooling behave consistently is the opposite of hiding it.
- Run a secret scan before pushing. Never commit `.env*` or credentials.

## Development workflow

See [docs/workstreams/README.md](./docs/workstreams/README.md). Work is backlog-driven: each
engineer keeps a worklog at `docs/workstreams/<name>.md` and normally takes the top open item.
Client priorities move and this is not a queue to defend: taking a lower item is fine, just say why
in the worklog so the order stays meaningful.
1. Fetch `main`; rebase if the worklog's base commit is behind.
2. Branch `feat/<name>/<slug>` off fresh `main`.
3. Quality standard: understand the task and code it touches; research library/API specifics
   (no guessing); **reuse before writing** (search for an existing helper; do not reinvent);
   smallest diff; root-cause bug-check; self-review (adversarial review if security-touching);
   lint/typecheck/test pass; PR with the evidence block.
4. Stay in your lane; shared contracts (`/services/api`, `/database`, `/schemas`) change only via
   Bhanu.
