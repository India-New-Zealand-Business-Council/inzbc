# Claude / contributor guidelines — INZBC platform

Repo-specific rules. General workflow is in [CONTRIBUTING.md](./CONTRIBUTING.md).

## Content

- Executive tone: professional, data-driven, politically neutral. No AI clichés.
- **Never invent** statistics, member counts, board names, or FTA details. Use sourced
  material only; leave `[[placeholders]]` where facts are owed by INZBC.
- Every AI-drafted output (digest, explainer, comms) needs a **named human reviewer** before
  publishing. `production_enabled` stays `false` until a formal launch approval exists.
- Handle member/personal data per the NZ Privacy Act 2020.

## The live site

- **Do not edit or publish `inzbc.org`.** Build the separate site; cut over at go-live only,
  after a backup and explicit sign-off.
- Wix MCP writes hit **live data instantly** (no draft). Do not point write calls at the live
  site. A publish guard hook (`wix-no-publish.sh`) blocks MCP publishes.

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
- Imperative commit subjects under ~60 chars. No AI attribution anywhere (commits, PRs, code).
- Run a secret scan before pushing. Never commit `.env*` or credentials.

## Development workflow

See [docs/workstreams/README.md](./docs/workstreams/README.md). Work is backlog-driven: each
engineer keeps a worklog at `docs/workstreams/<name>.md` and takes the top open item.
1. Fetch `main`; rebase if the worklog's base commit is behind.
2. Branch `feat/<name>/<slug>` off fresh `main`.
3. Quality standard: understand the task and code it touches; research library/API specifics
   (no guessing); **reuse before writing** (search for an existing helper; do not reinvent);
   smallest diff; root-cause bug-check; self-review (adversarial review if security-touching);
   lint/typecheck/test pass; PR with the evidence block.
4. Stay in your lane; shared contracts (`/services/api`, `/database`, `/schemas`) change only via
   Bhanu.
