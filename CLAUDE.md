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

## SIP (Trade Intelligence Platform)

- It is a **code application, not a Wix build** (Postgres, server-side model calls, auth,
  audit). See [docs/sip/README.md](./docs/sip/README.md). Security review before any staff use.

## Git

- Branch, open a PR into `main`. No direct pushes to `main`; only the tech lead merges.
- Imperative commit subjects under ~60 chars. No AI attribution anywhere (commits, PRs, code).
- Run a secret scan before pushing. Never commit `.env*` or credentials.
